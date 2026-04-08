import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps 
from pypdf import PdfWriter
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import io
import textwrap
import re
from datetime import datetime, timedelta
from streamlit_drawable_canvas import st_canvas
from email.header import Header
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from pillow_heif import register_heif_opener

# 아이폰 사진(HEIC) 호환 설정
register_heif_opener()

# --- [0] 세션 상태 초기화 ---
if 'submitting' not in st.session_state:
    st.session_state.submitting = False
if 'complete' not in st.session_state:
    st.session_state.complete = False

# --- 보안 설정 (Secrets 활용) ---
GMAIL_USER = st.secrets["GMAIL_USER"]
GMAIL_APP_PW = st.secrets["GMAIL_PW"]
RECEIVER_EMAIL = st.secrets["RECEIVER_EMAIL"]

# --- [보안 함수] 입력값 세탁 및 용량 체크 ---
def clean_text(text, max_len=100, allow_newline=False):
    if not text: return ""
    text = re.sub(r'<.*?>', '', text) # HTML 태그 제거
    if not allow_newline:
        text = text.replace('\n', ' ').replace('\r', ' ')
    return text.strip()[:max_len]

def check_file_size(file):
    if file is not None:
        if file.size > 10 * 1024 * 1024: # 10MB 제한
            return False
    return True

# --- [1] 메일 발송 함수 ---
def send_email(pdf_data, user_name, school_name):
    # 제목 인젝션 방어용 세탁
    clean_name = re.sub(r'[^\w\s]', '', user_name)
    clean_school = re.sub(r'[^\w\s]', '', school_name)
    
    msg = MIMEMultipart()
    msg['Subject'] = f"[배움터지킴이 지원 서류] {clean_school}-{clean_name}"
    msg['From'] = GMAIL_USER
    msg['To'] = RECEIVER_EMAIL
    
    body = f"{school_name} 배움터지킴이 지원 서류가 도착했습니다."
    msg.attach(MIMEText(body, 'plain'))
    
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(pdf_data)
    encoders.encode_base64(part)
    
    filename = f"{user_name}_{school_name}_배움터지킴이 지원 서류.pdf"
    part.add_header('Content-Disposition', 'attachment', filename=Header(filename, 'utf-8').encode())
    msg.attach(part)
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PW)
        server.send_message(msg)

# --- [2] 문서 생성 함수 ---
def make_documents(data, photo_file, sig_main, sig_pledge, sig_consent):
    img1 = Image.open("template01.jpg").convert("RGB")
    draw1 = ImageDraw.Draw(img1)
    font = ImageFont.truetype("malgun.ttf", 20) 
    font_addr = ImageFont.truetype("malgun.ttf", 15)
    font_title = ImageFont.truetype("malgunbd.ttf", 28)
    
    if photo_file:
        user_img = Image.open(photo_file).convert("RGB")
        user_img = ImageOps.exif_transpose(user_img)
        user_img = user_img.resize((171, 147))
        img1.paste(user_img, (710, 243))

    draw1.text((104, 181), data['school'] + "  ", fill="black", font=font_title)
    draw1.text((336, 474), data['school'], fill="black", font=font)
    draw1.text((260, 987), data['school'], fill="black", font=font)
    draw1.text((333, 254), data['name'], fill="black", font=font)
    draw1.text((430, 1121), data['name'], fill="black", font=font_title)
    draw1.text((333, 301), data['birth'], fill="black", font=font)
    
    addr_lines = textwrap.wrap(data['addr'], width=30)
    y_current = 345
    for line in addr_lines:
        draw1.text((326, y_current), line, fill="black", font=font_addr)
        y_current += 20

    draw1.text((445, 400), data['hphone'], fill="black", font=font)
    draw1.text((445, 428), data['phone'], fill="black", font=font)
    
    if data['has_exp'] == "있음": draw1.text((347, 610), "V", fill="black", font=font_title)
    else: draw1.text((412, 610), "V", fill="black", font=font_title)

    y_start = 567
    for exp in data['exp_list']:
        if exp['period'] or exp['agency']:
            draw1.text((460, y_start), exp['period'], fill="black", font=font_addr)
            draw1.text((672, y_start), exp['agency'], fill="black", font=font)
            y_start += 49
    
    draw1.text((336, 711), data['license'], fill="black", font=font) 
    draw1.text((336, 765), data['job'], fill="black", font=font)     
    draw1.text((336, 818), data['hobby'], fill="black", font=font)   
    
    motive_lines = textwrap.wrap(data['motive'], width=35)
    y_current = 863
    for line in motive_lines:
        draw1.text((329, y_current), line, fill="black", font=font)
        y_current += 20

    seoul_now = datetime.now() + timedelta(hours=9) 
    draw1.text((360, 1070), str(seoul_now.year), fill="black", font=font)
    draw1.text((469, 1070), str(seoul_now.month), fill="black", font=font)
    draw1.text((553, 1070), str(seoul_now.day), fill="black", font=font)

    img2 = Image.open("template02.jpg").convert("RGB")
    draw2 = ImageDraw.Draw(img2)
    
    draw2.text((606, 541), str(seoul_now.year), fill="black", font=font)
    draw2.text((715, 541), str(seoul_now.month), fill="black", font=font)
    draw2.text((797, 541), str(seoul_now.day), fill="black", font=font)
    draw2.text((623, 574), data['name'], fill="black", font=font_title)

    if data['agree1'] == "예": draw2.text((585, 880), "V", fill="black", font=font_title)
    if data['agree2'] == "예": draw2.text((585, 1060), "V", fill="black", font=font_title)
    if data['agree1'] == "아니요": draw2.text((716, 880), "V", fill="black", font=font_title)
    if data['agree2'] == "아니요": draw2.text((716, 1060), "V", fill="black", font=font_title)

    draw2.text((374, 1118), str(seoul_now.year), fill="black", font=font)
    draw2.text((481, 1118), str(seoul_now.month), fill="black", font=font)
    draw2.text((574, 1118), str(seoul_now.day), fill="black", font=font)
    draw2.text((457, 1155), data['name'], fill="black", font=font_title)

    def paste_sig(base_img, sig_raw, pos):
        if sig_raw is not None:
            s_img = Image.fromarray(sig_raw.astype('uint8'), 'RGBA').resize((150, 80))
            base_img.paste(s_img, pos, s_img)

    paste_sig(img1, sig_main, (600, 1100))
    paste_sig(img2, sig_pledge, (782, 555))
    paste_sig(img2, sig_consent, (605, 1135))

    results = []
    for i in [img1, img2]:
        buf = io.BytesIO()
        i.save(buf, format='JPEG', quality=50) # 압축
        results.append(buf.getvalue())
    return results

# --- [3] PDF 병합 함수 ---
def create_combined_pdf(pages_list, extra_files):
    writer = PdfWriter()
    w_a4, h_a4 = A4
    margin = 0.5 * cm
    draw_w, draw_h = w_a4 - (2 * margin), h_a4 - (2 * margin)

    for p_bytes in pages_list:
        tmp_buf = io.BytesIO()
        c = canvas.Canvas(tmp_buf, pagesize=A4)
        img = Image.open(io.BytesIO(p_bytes))
        c.drawInlineImage(img, 0, 0, width=w_a4, height=h_a4)
        c.showPage()
        c.save()
        tmp_buf.seek(0)
        writer.append(tmp_buf)

    for file, label in extra_files:
        if file is not None:
            file.seek(0)
            if file.name.lower().endswith('.pdf'):
                try: writer.append(file)
                except: continue
            else:
                try:
                    img = Image.open(file).convert("RGB")
                    img = ImageOps.exif_transpose(img)
                    img_w, img_h = img.size
                    ratio = min(draw_w / img_w, draw_h / img_h)
                    new_w, new_h = img_w * ratio, img_h * ratio
                    x, y = (w_a4 - new_w) / 2, (h_a4 - new_h) / 2
                    
                    img_buf = io.BytesIO()
                    img.save(img_buf, format='JPEG', quality=50) # 압축
                    img_buf.seek(0)
                    
                    tmp_buf = io.BytesIO()
                    c = canvas.Canvas(tmp_buf, pagesize=A4)
                    c.drawInlineImage(Image.open(img_buf), x, y, width=new_w, height=new_h)
                    c.showPage()
                    c.save()
                    tmp_buf.seek(0)
                    writer.append(tmp_buf)
                except: continue
    final_buf = io.BytesIO()
    writer.write(final_buf)
    return final_buf.getvalue()

# --- [4] 화면 UI (Streamlit) ---
st.set_page_config(page_title="배움터지킴이 서류 작성", layout="centered")
st.title("📄 부산 배움터지킴이 서류 작성")

if st.session_state.get('complete', False):
    st.success(f"🎉 서류 접수 완료했습니다.")
    st.balloons()
    st.info("💡 다시 작성하시려면 브라우저의 '새로고침' 버튼을 눌러주세요.")
    st.stop()

# 1. 학교명 파라미터 처리
url_school = st.query_params.get("school", "")

col1, col2 = st.columns(2)

# 1. URL에서 학교명 가져오기
url_school = st.query_params.get("school", "")

with col1:
    # 들여쓰기 주의! with col1 안쪽으로 다 들어와야 함
    if url_school:
        school = st.text_input("**지원 기관명**", value=url_school, disabled=True)
        st.caption(f"ℹ️ {url_school} 지원 페이지입니다.")
    else:
        school = st.text_input("**지원 기관명** (예: OO초등학교)", max_chars=30)
    
    # ⭐ [핵심] name과 birth는 if/else 밖으로 빼야 학교명이 고정되어도 보임!
    name = st.text_input("**지원자 성명**", max_chars=10)
    birth = st.text_input("**생년월일** (예: 1960.01.01)", max_chars=15)

with col2:
    hphone = st.text_input("**휴대전화 번호**", max_chars=15)
    phone = st.text_input("일반전화(없으면 비워두기)", max_chars=15)

addr = st.text_input("거주지 주소", max_chars=70)

# 경력 및 나머지 사항들
has_exp = st.radio("배움터지킴이 경력 유무(실적 증명서 제출 필수)", ["없음", "있음"], horizontal=True)

exp_data = []
if has_exp == "있음":
    for i in range(3):
        c_t, c_i = st.columns([1, 1])
        p = c_t.text_input(f"{i+1}. 활동 기간", key=f"p_{i}", max_chars=30)
        a = c_i.text_input(f"{i+1}. 기관명", key=f"a_{i}", max_chars=30)
        exp_data.append({"period": p, "agency": a})
else: 
    exp_data = [{"period": "", "agency": ""}] * 3

license = st.text_input("관련 자격증", max_chars=30)
job = st.text_input("직업(전직)", max_chars=15)
hobby = st.text_input("취미 및 특기", max_chars=30)
motive = st.text_area("지원 동기", max_chars=200)

with st.form("submit_section"):
    st.write("✒️ **위와 같이 배움터지킴이 자원봉사활동을 신청하며, 기재사항은 사실과 다름없음을 확인하고, 이에 서명합니다.**")
    canvas_main = st_canvas(stroke_width=3, stroke_color="black", background_color="rgba(0,0,0,0)", height=150, width=300, key="canvas_main")

    st.write("---")
    st.subheader("📁 서류 첨부")
    u_photo = st.file_uploader("본인 사진(되도록 증명사진이 좋음)", type=["jpg", "jpeg", "png"])
    
    col_p1, col_p2, col_p3 = st.columns(3)
    p1 = col_p1.file_uploader("실적 1", type=["jpg", "jpeg", "png", "pdf"], key="u_p1")
    p2 = col_p2.file_uploader("실적 2", type=["jpg", "jpeg", "png", "pdf"], key="u_p2")
    p3 = col_p3.file_uploader("실적 3", type=["jpg", "jpeg", "png", "pdf"], key="u_p3")

    col_l1, col_l2, col_l3 = st.columns(3)
    l1 = col_l1.file_uploader("자격증 1", type=["jpg", "jpeg", "png", "pdf"], key="u_l1")
    l2 = col_l2.file_uploader("자격증 2", type=["jpg", "jpeg", "png", "pdf"], key="u_l2")
    l3 = col_l3.file_uploader("자격증 3", type=["jpg", "jpeg", "png", "pdf"], key="u_l3")

    u_cert = st.file_uploader("직업(전직) 경력 증명서", type=["jpg", "jpeg", "png", "pdf"])
    u_etc = st.file_uploader("기타 서류", type=["jpg", "jpeg", "png", "pdf"])

    st.write("---")
    st.subheader("위촉 시 결격사유 없음 확인 절차")
    st.info("배움터지킴이 위촉 시 결격사유를 확인하시고, 결격사유에 해당되지 않을 경우 서명해 주십시오.")
    st.markdown("""
1.「국가공무원법」 제33조 각 호의 어느 하나에 해당하는 사람
            
2.「아동･청소년의 성보호에 관한 법률」에 따른 아동․청소년대상 성범죄 또는 「성폭력범죄의 처벌 등에 관한 특례법」에 따른 성폭력범죄를 저질러 벌금형을 선고받고 그 형이 확정된 날부터 10년이 지나지 아니하였거나, 금고 이상의 형이나 치료감호를 선고받고 그 집행이 끝나거나 집행이 유예․면제된 날부터 10년이 지나지 아니한 사람
            
3.「청소년 보호법」제2조 제5호 가목3) 및 같은 목 7)부터 9)까지의 청소년출입․고용금지업소의 업주나 종사자
            
4.「아동복지법」에 따라 아동학대관련 범죄로 형 또는 치료감호를 선고받아 확정되고, 그 확정된 때부터 형 또는 치료감호의 전부 또는 일부의 집행이 종료되거나 집행을 받지 아니하기로 확정된 후 10년이 경과하지 아니한 사람
""")

    canvas_sig1 = st_canvas(stroke_width=3, stroke_color="black", background_color="rgba(0,0,0,0)", height=150, width=300, key="canvas_sig1")
    agree1 = st.radio("개인정보 수집 및 이용 동의", ["예", "아니요"], index=0, key="agree1_btn")
    agree2 = st.radio("개인정보 제3자 제공 동의", ["예", "아니요"], index=0, key="agree2_btn")
    canvas_sig2 = st_canvas(stroke_width=3, stroke_color="black", background_color="rgba(0,0,0,0)", height=150, width=300, key="canvas_sig2")

    submit_clicked = st.form_submit_button("✅ 모든 서류 통합하여 제출하기", disabled=st.session_state.get('submitting', False))

# --- [5] 제출 로직 ---
if submit_clicked and not st.session_state.get('submitting', False):
    all_files = [u_photo, p1, p2, p3, l1, l2, l3, u_cert, u_etc]
    oversized = [f.name for f in all_files if f is not None and not check_file_size(f)]
    
    if not school or not name or not birth or not hphone:
        st.error("⚠️ 필수 항목을 입력해 주세요!")
    elif oversized:
        st.error(f"⚠️ 10MB 초과 파일: {', '.join(oversized)}")
    elif agree1 == "아니요" or agree2 == "아니요":
        st.error("⚠️ 개인정보 동의가 필요합니다.")
    elif not canvas_main.image_data.any() or not canvas_sig1.image_data.any() or not canvas_sig2.image_data.any():
        st.error("⚠️ 서명 3곳을 모두 완료해주세요.")
    else:
        st.session_state['submitting'] = True
        st.rerun()

if st.session_state.get('submitting', False):
    try:
        # 데이터 보안 세탁
        safe_data = {
            'school': clean_text(school, 30),
            'name': clean_text(name, 10),
            'birth': clean_text(birth, 15),
            'addr': clean_text(addr, 70),
            'hphone': clean_text(hphone, 15),
            'phone': clean_text(phone, 15),
            'has_exp': has_exp,
            'exp_list': [{"period": clean_text(e['period'], 30), "agency": clean_text(e['agency'], 30)} for e in exp_data],
            'license': clean_text(license, 30),
            'job': clean_text(job, 15),
            'hobby': clean_text(hobby, 30),
            'motive': clean_text(motive, 300, allow_newline=True),
            'agree1': agree1, 'agree2': agree2
        }

        with st.spinner("📦 지원 서류 생성 중..."):
            doc_pages = make_documents(safe_data, u_photo, canvas_main.image_data, canvas_sig1.image_data, canvas_sig2.image_data)
            
            # 첨부파일 정리
            u_perf = [(f, "실적") for f in [p1, p2, p3] if f]
            u_lic = [(f, "자격") for f in [l1, l2, l3] if f]
            extras = u_perf + u_lic
            if u_cert: extras.append((u_cert, "경력"))
            if u_etc: extras.append((u_etc, "기타"))
            
            final_pdf = create_combined_pdf(doc_pages, extras)
            send_email(final_pdf, safe_data['name'], safe_data['school'])
            
        st.session_state['submitting'] = False
        st.session_state['complete'] = True 
        st.rerun()
    except Exception as e:
        st.error(f"❌ 전송 오류: {e}")
        st.session_state['submitting'] = False
        st.rerun()