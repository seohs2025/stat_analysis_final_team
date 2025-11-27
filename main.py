import json
import openai
from dotenv import load_dotenv
import os
import random
import re

# ===== 환경 설정 =====
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
client = openai.Client()

TOTAL_QUESTIONS = 6

SKIP_KEYWORDS = [
    "다음 질문", "다음질문", "스킵", "skip", "pass", "next",
    "next question", "넘어가기", "넘어가자", "넘어갈게요"
]

# 태도/모범/성실 칭찬만 제거
EXCLUDE_KEYWORDS = [
    "성실", "성실함", "성실하게", "모범", "모범적인",
    "태도", "태도가", "자세가 좋", "정성을 다해",
    "발표한 모습이 보기 좋았", "발표를 잘함", "발표를 잘 하",
    "참여도가 높", "열심히 참여", "적극적으로 참여",
    "친구들과 잘 지내", "봉사정신이 투철", "예의바른 태도"
]

# 희망 분야 매핑
CAREER_SUBJECT_MAP = {
    "공학": ["수학", "기하", "미적", "미적분", "과학", "물리",
           "융합과학", "정보", "프로그래밍", "공학", "인공지능 수학"],
    "자연": ["생명", "생명과학", "화학", "지구", "지구과학", "물리", "과학"],
    "의학": ["생명", "생명과학", "화학", "보건", "의학"],
    "컴퓨터": ["정보", "프로그래밍", "AI", "데이터", "수학",
            "기하", "미적분", "인공지능 수학", "컴퓨터공학"],
    "소프트웨어": ["정보", "프로그래밍", "AI", "컴퓨터", "수학"],
    "AI": ["정보", "프로그래밍", "AI", "융합과학", "수학", "인공지능 수학"],
    "상경": ["경제", "사회", "정치", "수학", "확률과통계"],
    "경영": ["경영", "경제", "사회", "수학"],
    "인문": ["국어", "문학", "독서", "사회", "윤리", "철학"],
    "교육": ["교육", "심리", "국어", "사회"]
}

##########################################################
# 1. 전체 텍스트 합치기
##########################################################
def get_full_text(student_data):
    records = student_data.get("academic_records", [])
    if isinstance(records, list):
        full = "\n".join(str(x) for x in records)
    else:
        full = str(records)

    reading = student_data.get("reading", "")
    if reading:
        full += "\n" + str(reading)

    return full


##########################################################
# 2. 희망분야 → 학년별 자동 배정
##########################################################
def extract_career_by_grade(full_text):
    matches = re.findall(r"희망\s*분야\s*([^\n]+)", full_text)

    grade_raw = {1: None, 2: None, 3: None}
    for idx, raw in enumerate(matches[:3], start=1):
        cleaned = raw.replace("분야", "").replace("계열", "").strip()
        grade_raw[idx] = cleaned

    def normalize(field):
        if not field:
            return ""
        if "컴퓨터" in field or "소프트웨어" in field:
            return "컴퓨터"
        if "ai" in field.lower():
            return "AI"
        if "공학" in field:
            return "공학"
        if "자연" in field:
            return "자연"
        if "의학" in field:
            return "의학"
        if "경영" in field:
            return "경영"
        if "상경" in field:
            return "상경"
        if "인문" in field:
            return "인문"
        if "교육" in field:
            return "교육"
        return field

    grade_norm = {g: normalize(v) for g, v in grade_raw.items()}
    return grade_raw, grade_norm


##########################################################
# 3. 세특/창체 출처 자동 추출
##########################################################
def extract_sources(full_text):
    sources = []

    # 3-1) 세부능력특기사항
    pattern = re.compile(
        r"([가-힣A-Za-z0-9\s]+):\s*(.+?)(?=\n[가-힣A-Za-z0-9\s]+:|\n동아리활동|\n자율활동|\n진로활동|\n봉사활동|\Z)",
        re.DOTALL
    )

    for m in pattern.finditer(full_text):
        subject = m.group(1).strip()
        desc = m.group(2).strip().replace("\n", " ")[:250]
        label = f"{subject}(세부능력특기사항)"
        sources.append((label, desc))

    # 3-2) 창체
    blocks = ["동아리활동", "자율활동", "진로활동", "봉사활동"]
    for b in blocks:
        bpat = re.compile(
            b + r"\s*\n(.+?)(?=\n동아리활동|\n자율활동|\n진로활동|\n봉사활동|\Z)",
            re.DOTALL
        )
        for m in bpat.finditer(full_text):
            desc = m.group(1).strip().replace("\n", " ")[:250]
            sources.append((b, desc))

    return sources


##########################################################
# 4. 태도성 내용 제거
##########################################################
def filter_out_attitude(sources):
    clean = []
    for label, text in sources:
        combo = label + " " + text
        if not any(bad in combo for bad in EXCLUDE_KEYWORDS):
            clean.append((label, text))
    return clean


##########################################################
# 5. label → 과목명/활동종류 분리
##########################################################
def split_label(label):
    """
    label 예:
    - '인공지능 수학(세부능력특기사항)'
    - '동아리활동'
    """
    if "(" in label:
        subject = label.split("(")[0]
        activity = label[label.find("(")+1:-1]
    else:
        subject = label
        activity = "창체활동"

    return subject.strip(), activity.strip()


##########################################################
# 6. 메인 로직
##########################################################
def start_ai_interview(student_data):
    full_text = get_full_text(student_data)

    # --- 희망분야 추출 ---
    career_raw, career_norm = extract_career_by_grade(full_text)

    print("\n=== 희망분야 인식 결과 ===")
    for g in [1,2,3]:
        print(f"{g}학년 → {career_raw.get(g)} (키워드: {career_norm.get(g)})")
    print("==========================\n")

    # --- 출처 추출 ---
    sources = extract_sources(full_text)
    sources = filter_out_attitude(sources)

    if not sources:
        print("출처 없음. JSON 구조 확인 필요.")
        return

    # --- A 모드 SYSTEM PROMPT ---
    system_prompt = '''
너는 대한민국 최상위권 공대 면접관이다.
매우 냉정하고 날카롭게 평가하며 생기부와 무관한 답변은 모두 혹평하라.
점수 < 70점이면 반드시 [다시 답변 요청]을 붙인다.
'''

    messages = [{"role": "system", "content": system_prompt}]

    question_num = 1

    while question_num <= TOTAL_QUESTIONS:

        # === 1) 학년 랜덤 선택 ===
        selected_grade = random.choice([1,2,3])
        selected_career_raw = career_raw[selected_grade]
        selected_career_norm = career_norm[selected_grade]

        # === 2) 해당 학년 희망분야 기반 필터 ===
        allowed_keywords = CAREER_SUBJECT_MAP.get(selected_career_norm, [])
        grade_sources = [
            s for s in sources if any(k in (s[0] + s[1]) for k in allowed_keywords)
        ]
        if not grade_sources:
            grade_sources = sources

        # === 3) 출처 선택 ===
        label, text = random.choice(grade_sources)
        subject_name, activity_type = split_label(label)

        is_last = (question_num == TOTAL_QUESTIONS)

        # === 4) 질문 생성 ===
        user_prompt = f'''
다음 정보를 기반으로 {"[마지막 질문]" if is_last else "[질문]"}을 생성하라.

출처 학년: {selected_grade}학년
과목명: {subject_name}
활동종류: {activity_type}
출처 전문: {label}
핵심 내용: {text}

해당 학년 희망분야: {selected_career_raw} (키워드: {selected_career_norm})

형식:
{"[마지막 질문]" if is_last else "[질문]"}
출처: {selected_grade}학년 · {subject_name} ({activity_type})
희망분야({selected_grade}학년): {selected_career_raw}
핵심 내용: {text}
질문:
'''
        messages.append({"role": "user", "content": user_prompt})

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=600
        )
        qtext = resp.choices[0].message.content
        print("\n" + qtext)
        messages.append({"role": "assistant", "content": qtext})

        # === 5) 답변 받기 ===
        answer = input("\n[학생 답변 또는 '다음 질문'] > ")

        if any(k in answer.lower() for k in SKIP_KEYWORDS):
            print("\n[안내] 다음 질문으로 넘어갑니다.\n")
            question_num += 1
            continue

        if answer.lower() in ("exit", "quit"):
            print("면접을 종료합니다.")
            break

        # === 6) 평가 ===
        eval_prompt = f'''
[학생 답변]
{answer}

출처 학년: {selected_grade}학년
과목명: {subject_name}
활동종류: {activity_type}
출처 전문: {label}
핵심 내용: {text}
희망분야({selected_grade}학년): {selected_career_raw}

A 모드로 매우 날카롭게 평가하라.
'''
        messages.append({"role": "user", "content": eval_prompt})

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=900
        )
        eval_text = resp.choices[0].message.content
        print("\n" + eval_text)
        messages.append({"role": "assistant", "content": eval_text})

        if "[다시 답변 요청]" in eval_text:
            continue

        question_num += 1


##########################################################
# 실행
##########################################################
if __name__ == "__main__":
    with open("wnskadud_structured (1).json", "r", encoding="utf-8") as f:
        data = json.load(f)

    start_ai_interview(data)
