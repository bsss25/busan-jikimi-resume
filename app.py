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
import base64
from datetime import datetime, timedelta
from streamlit_drawable_canvas import st_canvas
from email.header import Header
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from pillow_heif import register_heif_opener
# PDF 변환을 위한 라이브러리 추가
try:
    import fitz 
except ImportError:
    pass

# 아이폰 사진(HEIC) 호환 설정
register_heif_opener()

# --- [0] 세션 상태 초기화 ---
if 'step' not in st.session_state: st.session_state.step = 'edit'
if 'temp_pdf' not in st.session_state: st.session_state.temp_pdf = None
if 'preview_images' not in st.session_state: st.session_state.preview_images = []
if 'preview_captions' not in st.session_state: st.session_state.preview_captions = []
if 'safe_data' not in st.session_state: st.session_state.safe_data = {}

# 입력값 보존을 위한 초기화
fields = ['school_val', 'name_val', 'birth_val', 'hphone_val', 'phone_val', 'addr_val', 'license_val', 'job_val', 'hobby_val', 'motive_val']
for f in fields:
    if f not in st.session_state: st.session_state[f] = ""
if 'has_exp_val' not in st.session_state: st.session_state.has_exp_val = "없음"
if 'exp_data_val' not in st.session_state: st.session_state.exp_data_val = [{"period": "", "agency": ""}] * 3

# --- 보안 설정 (Secrets 활용) ---
GMAIL_USER = st.secrets["GMAIL_USER"]
GMAIL_APP_PW = st.secrets["GMAIL_APP_PW"]
RECEIVER_EMAIL = st.secrets["RECEIVER_EMAIL"]

# --- [보안/편의 함수] ---
def clean_text(text, max_len=100, allow_newline=False):
    if not text: return ""
    text = re.sub(r'<.*?>', '', text)
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
    msg = MIMEMultipart()
    msg['Subject'] = f"[배움터지킴이 지원 서류] {school_name}-{user_name}"
    msg['From'] = GMAIL_USER
    msg['To'] = RECEIVER_EMAIL
    body = f"{school_name} 배움터지킴이 지원 서류가 도착했습니다."
    msg.attach(MIMEText(body, 'plain'))
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(pdf_data)
    encoders.encode_base64(part)
    filename = f"{user_name}_{school_name}_지원서류.pdf"
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
                try: 
                    file.seek(0)
                    writer.append(file)
                except: continue
            else:
                try:
                    img = Image.open(file).convert("RGB")
                    # 메인 PDF 생성시에도 회전 문제 해결
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

# --- [4] 화면 UI ---
st.set_page_config(page_title="배움터지킴이 서류 작성", layout="centered")

# [1] 작성 페이지
if st.session_state.step == 'edit':
    st.title("📄 부산 배움터지킴이 서류 작성")
    
    url_school = st.query_params.get("school", "")
    col1, col2 = st.columns(2)
    with col1:
        if url_school:
            school = st.text_input("**지원 기관명**", value=url_school, disabled=True)
        else:
            school = st.text_input("**지원 기관명** (예: OO초등학교)", value=st.session_state.school_val, max_chars=30)
        
        name = st.text_input("**지원자 성명**", value=st.session_state.name_val, max_chars=10)
        birth = st.text_input("**생년월일** (예: 1960.01.01)", value=st.session_state.birth_val, max_chars=15)
    with col2:
        hphone = st.text_input("**휴대전화 번호**", value=st.session_state.hphone_val, max_chars=15)
        phone = st.text_input("일반전화(없으면 비워두기)", value=st.session_state.phone_val, max_chars=15)
    
    addr = st.text_input("거주지 주소", value=st.session_state.addr_val, max_chars=70)

    exp_idx = 0 if st.session_state.has_exp_val == "없음" else 1
    has_exp = st.radio("배움터지킴이 경력 유무(실적 증명서 제출 필수)", ["없음", "있음"], index=exp_idx, horizontal=True)
    
    exp_data = []
    if has_exp == "있음":
        for i in range(3):
            c_t, c_i = st.columns([1, 1])
            p = c_t.text_input(f"{i+1}. 활동 기간", value=st.session_state.exp_data_val[i]['period'], key=f"p_{i}", max_chars=30)
            a = c_i.text_input(f"{i+1}. 기관명", value=st.session_state.exp_data_val[i]['agency'], key=f"a_{i}", max_chars=30)
            exp_data.append({"period": p, "agency": a})
    else: exp_data = [{"period": "", "agency": ""}] * 3

    license = st.text_input("관련 자격증", value=st.session_state.license_val, max_chars=30)
    job = st.text_input("직업(전직)", value=st.session_state.job_val, max_chars=15)
    hobby = st.text_input("취미 및 특기", value=st.session_state.hobby_val, max_chars=30)
    motive = st.text_area("지원 동기", value=st.session_state.motive_val, max_chars=200)

    with st.form("submit_section"):
        st.write("✒️ **위와 같이 배움터지킴이 자원봉사활동을 신청하며, 기재사항은 사실과 다름없음을 확인하고, 이에 서명합니다.**")
        st.caption("⚠️ 주의: 서명은 '미리보기' 클릭 전 마지막에 해주세요. (수정 시 다시 서명 필요)")
        canvas_main = st_canvas(stroke_width=3, stroke_color="black", background_color="rgba(0,0,0,0)", height=150, width=300, key="canvas_main")

        st.write("---")
        st.subheader("📁 서류 첨부")
        u_photo = st.file_uploader("본인 사진(되도록 증명사진이 좋음)", type=["jpg", "jpeg", "png"])
        
        st.write("배움터지킴이 활동 실적 확인서(최대 3개)")
        col_p = st.columns(3)
        p1 = col_p[0].file_uploader("배움터지킴이 활동 실적 1", type=["jpg", "jpeg", "png", "pdf"], key="u_p1")
        p2 = col_p[1].file_uploader("배움터지킴이 활동 실적 2", type=["jpg", "jpeg", "png", "pdf"], key="u_p2")
        p3 = col_p[2].file_uploader("배움터지킴이 활동 실적 3", type=["jpg", "jpeg", "png", "pdf"], key="u_p3")

        st.write("관련 자격증(최대 3개)")
        col_l = st.columns(3)
        l1 = col_l[0].file_uploader("자격증 1", type=["jpg", "jpeg", "png", "pdf"], key="u_l1")
        l2 = col_l[1].file_uploader("자격증 2", type=["jpg", "jpeg", "png", "pdf"], key="u_l2")
        l3 = col_l[2].file_uploader("자격증 3", type=["jpg", "jpeg", "png", "pdf"], key="u_l3")

        u_cert = st.file_uploader("직업(전직) 경력 증명서", type=["jpg", "jpeg", "png", "pdf"])
        u_etc = st.file_uploader("기타 서류", type=["jpg", "jpeg", "png", "pdf"])

        st.write("---")
        st.subheader("위촉 시 결격사유 없음 확인 절차")
        st.markdown("""
1.「국가공무원법」 제33조 각 호의 어느 하나에 해당하는 사람
            
2.「아동･청소년의 성보호에 관한 법률」에 따른 아동․청소년대상 성범죄 또는 「성폭력범죄의 처벌 등에 관한 특례법」에 따른 성폭력범죄를 저질러 벌금형을 선고받고 그 형이 확정된 날부터 10년이 지나지 아니하였거나, 금고 이상의 형이나 치료감호를 선고받고 그 집행이 끝나거나 집행이 유예․면제된 날부터 10년이 지나지 아니한 사람
            
3.「청소년 보호법」제2조 제5호 가목3) 및 같은 목 7)부터 9)까지의 청소년출입․고용금지업소의 업주나 종사자
            
4.「아동복지법」에 따라 아동학대관련 범죄로 형 또는 치료감호를 선고받아 확정되고, 그 확정된 때부터 형 또는 치료감호의 전부 또는 일부의 집행이 종료되거나 집행을 받지 아니하기로 확정된 후 10년이 경과하지 아니한 사람
""")
        canvas_sig1 = st_canvas(stroke_width=3, stroke_color="black", background_color="rgba(0,0,0,0)", height=150, width=300, key="canvas_sig1")

        st.write("---")
        st.subheader("개인정보 수집 및 제3자 제공 동의 절차")
        st.info("부산광역시교육청학교행정지원본부는 다음과 같이 개인정보를 수집‧이용합니다.")
        st.markdown("""           
* **개인정보 수집 항목:** 성명, 생년월일, 주소, 연락처 등
* **수집 목적:** 배움터지킴이 자원봉사자 위촉
* **보유 기간:** 1년
""")
        agree1 = st.radio("개인정보 수집 및 이용 동의", ["예", "아니요"], index=0, key="agree1_btn")

        st.info("부산광역시교육청학교행정지원본부는 다음과 같이 개인정보를 제3자에게 제공할 수 있습니다.")
        st.markdown("""             
* **제공받는 기관:** 부산 관내 학교(유치원)
* **제공 목적:** 배움터지킴이 자원봉사자 위촉
* **제공 항목:** 성명, 생년월일, 주소, 연락처, 희망학교, 경력, 자격 등
* **보유 기간:** 1년
""")
        agree2 = st.radio("개인정보 제3자 제공 동의", ["예", "아니요"], index=0, key="agree2_btn")
        canvas_sig2 = st_canvas(stroke_width=3, stroke_color="black", background_color="rgba(0,0,0,0)", height=150, width=300, key="canvas_sig2")

        preview_clicked = st.form_submit_button("🔍 내가 작성한 지원서 보기 및 제출")

    if preview_clicked:
        # **입력값 세션 저장**
        st.session_state.update({
            'school_val': school, 'name_val': name, 'birth_val': birth, 'hphone_val': hphone,
            'phone_val': phone, 'addr_val': addr, 'has_exp_val': has_exp, 'exp_data_val': exp_data,
            'license_val': license, 'job_val': job, 'hobby_val': hobby, 'motive_val': motive
        })

        if not school or not name or not birth or not hphone:
            st.error("⚠️ 지원 기관명, 성명, 생년월일, 휴대폰 번호는 필수 입력 항목입니다!")
        elif agree1 == "아니요" or agree2 == "아니요":
            st.error("⚠️ 개인정보 수집·이용·제3자제공 동의가 필요합니다.")
        elif not canvas_main.image_data.any() or not canvas_sig1.image_data.any() or not canvas_sig2.image_data.any():
            st.error("⚠️ 서명 3곳을 모두 완료해주세요.")
        else:
            with st.spinner("📦 미리보기 파일을 생성 중..."):
                st.session_state.safe_data = {
                    'school': clean_text(school, 30), 'name': clean_text(name, 10),
                    'birth': clean_text(birth, 15), 'addr': clean_text(addr, 70),
                    'hphone': clean_text(hphone, 15), 'phone': clean_text(phone, 15),
                    'has_exp': has_exp, 'exp_list': exp_data, 'license': license,
                    'job': job, 'hobby': hobby, 'motive': motive,
                    'agree1': agree1, 'agree2': agree2
                }
                
                # 1. 지원서 이미지 생성
                doc_pages = make_documents(st.session_state.safe_data, u_photo, canvas_main.image_data, canvas_sig1.image_data, canvas_sig2.image_data)
                
                # 2. 첨부파일 리스트 정리 (PDF 생성용)
                u_perf = [(f, "실적") for f in [p1, p2, p3] if f]
                u_lic = [(f, "자격") for f in [l1, l2, l3] if f]
                extras = u_perf + u_lic
                if u_cert: extras.append((u_cert, "경력"))
                if u_etc: extras.append((u_etc, "기타"))
                
                # ⭐ [수정된 미리보기 이미지 합치기] 지원서 2장 + 첨부파일(이미지 및 PDF 전 페이지)
                preview_list = list(doc_pages)
                preview_caps = ["1페이지(지원서)", "2페이지(동의서)"]
                
                for f, label in extras:
                    f.seek(0)
                    # 1. 이미지 파일 처리 (폰 회전 문제 해결 추가)
                    if f.name.lower().endswith(('.jpg', '.jpeg', '.png')):
                        try:
                            # PIL로 열고 EXIF 정보 기준으로 회전 적용
                            temp_img = Image.open(f)
                            temp_img = ImageOps.exif_transpose(temp_img)
                            # byte stream으로 변환하여 미리보기 리스트에 추가
                            temp_buf = io.BytesIO()
                            temp_img.save(temp_buf, format='JPEG', quality=75) # Decent quality for preview
                            preview_list.append(temp_buf.getvalue())
                            preview_caps.append(f"첨부파일 - {label}")
                        except:
                            # 이미지 로드 실패 시 원본 그대로 시도 (비 HEIC 등)
                            f.seek(0)
                            preview_list.append(f.read())
                            preview_caps.append(f"첨부파일 - {label}")
                    
                    # 2. PDF 파일 처리
                    elif f.name.lower().endswith('.pdf'):
                        try:
                            pdf_doc = fitz.open(stream=f.read(), filetype="pdf")
                            for page_num in range(len(pdf_doc)):
                                page = pdf_doc.load_page(page_num)
                                pix = page.get_pixmap()
                                # 리스트에 이미지와 자막을 '동시에' 추가해야 에러가 안 납니다!
                                preview_list.append(pix.tobytes("png"))
                                preview_caps.append(f"첨부파일({label}) - {page_num + 1}쪽")
                            pdf_doc.close()
                        except:
                            # 변환 실패하면 아예 리스트에 아무것도 안 넣거나, 둘 다 넣어야 함
                            # 여기서는 안전하게 아무것도 넣지 않고 넘어갑니다.
                            pass 
                
                st.session_state.preview_images = preview_list
                st.session_state.preview_captions = preview_caps
                
                # 3. 최종 PDF 데이터 생성
                st.session_state.temp_pdf = create_combined_pdf(doc_pages, extras)
                st.session_state.step = 'preview'
                st.rerun()

# [2] 미리보기 페이지
elif st.session_state.step == 'preview':
    st.title("🔍 서류 확인 및 최종 제출")
    st.info("💡 서류와 첨부파일을 확인해주세요. 내용이 맞으면 아래 '🚀 최종 제출하기' 버튼을 눌러주세요.")
    
    # ⭐ 지원서 + 첨부이미지 모두 출력
    if st.session_state.preview_images:
        st.image(
            st.session_state.preview_images, 
            caption=st.session_state.get('preview_captions', []), 
            use_container_width=True
        )

    st.write("---")
    col_save, col_submit, col_back = st.columns(3)
    
    with col_save:
        st.download_button("💾 내 기기에 저장하기", st.session_state.temp_pdf, f"{st.session_state.safe_data['name']}_지원서.pdf", "application/pdf")
    
    with col_submit:
        if st.button("🚀 최종 제출하기"):
            try:
                with st.spinner("📧 서류를 전송 중..."):
                    send_email(st.session_state.temp_pdf, st.session_state.safe_data['name'], st.session_state.safe_data['school'])
                    st.session_state.step = 'complete'
                    st.rerun()
            except Exception as e:
                st.error(f"❌ 전송 오류: {e}")

    with col_back:
        if st.button("⬅️ 수정하러 가기"):
            st.session_state.step = 'edit'
            st.rerun()

# [3] 완료 페이지
elif st.session_state.step == 'complete':
    st.success(f"🎉 {st.session_state.safe_data['name']} 선생님, 서류 접수가 완료되었습니다.")
    st.balloons()
    st.info("💡 제출된 서류는 담당자 메일로 안전하게 전송되었습니다. 다시 작성하시려면 아래 버튼을 눌러주세요.")
    if st.button("처음으로 돌아가기"):
        st.session_state.clear()
        st.session_state.step = 'edit'
        st.rerun()