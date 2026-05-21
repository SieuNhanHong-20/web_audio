import asyncio
import os
import uuid
import json
import time
import threading
from flask import Flask, request, jsonify, send_file, Response, stream_with_context
from flask_cors import CORS
import edge_tts
from pydub import AudioSegment
import tempfile

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Lưu trạng thái tiến trình theo job_id
job_progress = {}

CHINESE_VOICES = [
    {"id": "zh-CN-XiaoxiaoNeural",    "name": "晓晓 Xiǎoxiāo",  "gender": "Nữ",  "style": "Ấm áp, tự nhiên – rất phổ biến cho podcast"},
    {"id": "zh-CN-XiaoyiNeural",      "name": "晓伊 Xiǎoyī",    "gender": "Nữ",  "style": "Trẻ trung, sống động"},
    {"id": "zh-CN-XiaohanNeural",     "name": "晓涵 Xiǎohán",   "gender": "Nữ",  "style": "Nhẹ nhàng, chuyên nghiệp"},
    {"id": "zh-CN-XiaoqiuNeural",     "name": "晓秋 Xiǎoqiū",   "gender": "Nữ",  "style": "Trưởng thành, sâu lắng"},
    {"id": "zh-CN-XiaoshuangNeural",  "name": "晓双 Xiǎoshuāng","gender": "Nữ",  "style": "Hoạt bát, vui vẻ"},
    {"id": "zh-CN-XiaozhenNeural",    "name": "晓甄 Xiǎozhēn",  "gender": "Nữ",  "style": "Chính thức, rõ ràng"},
    {"id": "zh-CN-YunxiNeural",       "name": "云希 Yúnxī",     "gender": "Nam", "style": "Tự nhiên, thân thiện – tốt cho podcast nam"},
    {"id": "zh-CN-YunjianNeural",     "name": "云健 Yúnjiàn",   "gender": "Nam", "style": "Mạnh mẽ, tự tin"},
    {"id": "zh-CN-YunxiaNeural",      "name": "云夏 Yúnxià",    "gender": "Nam", "style": "Trẻ trung, nhẹ nhàng"},
    {"id": "zh-CN-YunyangNeural",     "name": "云扬 Yúnyáng",   "gender": "Nam", "style": "Chuyên nghiệp, báo chí"},
    {"id": "zh-TW-HsiaoChenNeural",   "name": "曉臻 Xiǎozhēn",  "gender": "Nữ",  "style": "Tiếng Đài Loan, thanh lịch"},
    {"id": "zh-TW-YunJheNeural",      "name": "雲哲 Yúnzhé",    "gender": "Nam", "style": "Tiếng Đài Loan, rõ ràng"},
    {"id": "zh-HK-HiuMaanNeural",     "name": "曉曼 Xiǎomàn",   "gender": "Nữ",  "style": "Tiếng Quảng Đông, nữ"},
    {"id": "zh-HK-WanLungNeural",     "name": "雲龍 Yúnlóng",   "gender": "Nam", "style": "Tiếng Quảng Đông, nam"},
]

def split_text(text, max_chars=800):
    """Chia văn bản dài thành các đoạn nhỏ, cố gắng cắt ở dấu câu."""
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    current = ""
    
    # Ưu tiên cắt ở: dấu chấm câu tiếng Trung, tiếng Anh
    sentence_endings = ['。', '！', '？', '…', '.', '!', '?', '\n']
    
    i = 0
    while i < len(text):
        current += text[i]
        
        # Nếu đạt giới hạn, tìm điểm cắt phù hợp
        if len(current) >= max_chars:
            # Tìm ngược về dấu câu gần nhất trong 100 ký tự cuối
            cut_pos = -1
            for j in range(len(current)-1, max(len(current)-100, 0)-1, -1):
                if current[j] in sentence_endings:
                    cut_pos = j
                    break
            
            if cut_pos > 0:
                chunks.append(current[:cut_pos+1].strip())
                current = current[cut_pos+1:]
            else:
                # Không tìm thấy dấu câu, cắt cứng
                chunks.append(current.strip())
                current = ""
        i += 1
    
    if current.strip():
        chunks.append(current.strip())
    
    return [c for c in chunks if c]


async def synthesize_chunk(text, voice, output_path):
    """Tổng hợp giọng nói cho một đoạn văn bản."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def synthesize_full(text, voice, job_id):
    """Xử lý toàn bộ văn bản, ghép MP3, cập nhật tiến trình."""
    try:
        job_progress[job_id] = {"status": "processing", "percent": 0, "message": "Đang chia đoạn văn bản..."}
        
        chunks = split_text(text, max_chars=800)
        total = len(chunks)
        chunk_files = []
        
        job_progress[job_id]["message"] = f"Tổng cộng {total} đoạn, bắt đầu tổng hợp..."
        
        for idx, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            
            tmp_path = os.path.join(OUTPUT_DIR, f"{job_id}_chunk_{idx}.mp3")
            chunk_files.append(tmp_path)
            
            # Chạy async trong thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(synthesize_chunk(chunk, voice, tmp_path))
            loop.close()
            
            percent = int((idx + 1) / total * 85)
            job_progress[job_id] = {
                "status": "processing",
                "percent": percent,
                "message": f"Đã xử lý {idx+1}/{total} đoạn..."
            }
        
        # Ghép tất cả chunk lại
        job_progress[job_id] = {"status": "processing", "percent": 88, "message": "Đang ghép file audio..."}
        
        final_path = os.path.join(OUTPUT_DIR, f"{job_id}_final.mp3")
        
        if len(chunk_files) == 1:
            os.rename(chunk_files[0], final_path)
        else:
            combined = AudioSegment.empty()
            for cf in chunk_files:
                if os.path.exists(cf):
                    seg = AudioSegment.from_mp3(cf)
                    combined += seg
            combined.export(final_path, format="mp3", bitrate="192k")
            # Xóa chunk tạm
            for cf in chunk_files:
                if os.path.exists(cf):
                    os.remove(cf)
        
        job_progress[job_id] = {
            "status": "done",
            "percent": 100,
            "message": "Hoàn thành!",
            "file": f"{job_id}_final.mp3"
        }
    
    except Exception as e:
        job_progress[job_id] = {
            "status": "error",
            "percent": 0,
            "message": f"Lỗi: {str(e)}"
        }
        # Dọn dẹp file tạm nếu có lỗi
        for cf in chunk_files if 'chunk_files' in dir() else []:
            if os.path.exists(cf):
                os.remove(cf)


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/voices", methods=["GET"])
def get_voices():
    return jsonify(CHINESE_VOICES)


@app.route("/synthesize", methods=["POST"])
def synthesize():
    data = request.get_json()
    text = (data.get("text") or "").strip()
    voice = data.get("voice", "zh-CN-XiaoxiaoNeural")
    
    if not text:
        return jsonify({"error": "Vui lòng nhập văn bản"}), 400
    if len(text) > 50000:
        return jsonify({"error": "Văn bản tối đa 50.000 ký tự"}), 400
    
    job_id = str(uuid.uuid4()).replace("-", "")
    job_progress[job_id] = {"status": "queued", "percent": 0, "message": "Đang chuẩn bị..."}
    
    # Chạy tổng hợp trong background thread
    t = threading.Thread(target=synthesize_full, args=(text, voice, job_id))
    t.daemon = True
    t.start()
    
    return jsonify({"job_id": job_id})


@app.route("/progress/<job_id>", methods=["GET"])
def progress(job_id):
    """SSE endpoint để stream tiến trình realtime."""
    def generate():
        while True:
            info = job_progress.get(job_id, {"status": "not_found", "percent": 0, "message": "Không tìm thấy job"})
            yield f"data: {json.dumps(info)}\n\n"
            
            if info["status"] in ("done", "error"):
                break
            time.sleep(0.5)
    
    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@app.route("/download/<job_id>", methods=["GET"])
def download(job_id):
    info = job_progress.get(job_id)
    if not info or info.get("status") != "done":
        return jsonify({"error": "File chưa sẵn sàng"}), 404
    
    file_path = os.path.join(OUTPUT_DIR, info["file"])
    if not os.path.exists(file_path):
        return jsonify({"error": "File không tồn tại"}), 404
    
    response = send_file(
        file_path,
        as_attachment=True,
        download_name="podcast_chinese.mp3",
        mimetype="audio/mpeg"
    )
    
    # Xóa file sau khi gửi (dùng callback)
    @response.call_on_close
    def cleanup():
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            if job_id in job_progress:
                del job_progress[job_id]
        except Exception:
            pass
    
    return response


@app.route("/preview", methods=["POST"])
def preview():
    """Tổng hợp nhanh 200 ký tự đầu để nghe thử."""
    data = request.get_json()
    text = (data.get("text") or "").strip()[:200]
    voice = data.get("voice", "zh-CN-XiaoxiaoNeural")
    
    if not text:
        return jsonify({"error": "Vui lòng nhập văn bản"}), 400
    
    tmp_path = os.path.join(OUTPUT_DIR, f"preview_{uuid.uuid4().hex}.mp3")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(synthesize_chunk(text, voice, tmp_path))
    loop.close()
    
    response = send_file(tmp_path, mimetype="audio/mpeg")
    
    @response.call_on_close
    def cleanup():
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
    
    return response


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
