import json
import openai
from dotenv import load_dotenv
import os

# 환경 변수 로드
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# OpenAI 클라이언트 생성 (2.x)
client = openai.Client()

# 생성할 총 질문 수
TOTAL_QUESTIONS = 6


def build_student_summary(data):
    """생기부 JSON에서 면접용 요약 생성"""
    name = data["student_info"]["name"]

    # 수상 경력 요약
    awards_list = [a.get("award_name", "") for a in data.get("awards", [])]
    awards = ", ".join(awards_list) if awards_list else "없음"

    # 학업 관련 기록 정리
    academic_text = ""
    for rec in data.get("academic_records", []):
        if isinstance(rec, str):
            academic_text += rec + "\n"

    academic_text = academic_text[:2000]

    return f"""
이름: {name}
수상경력: {awards}

창의적 체험활동 / 교과 세부능력 주요 내용:
{academic_text}
"""


def start_ai_interview(student_data):
    summary = build_student_summary(student_data)

    # SYSTEM 프롬프트 — 규칙 강화
    system_prompt = f"""
당신은 대한민국 대입 전문 면접관입니다.

학생의 생기부 요약:
{summary}

면접 규칙:
1) 첫 질문은 아래 형식으로만 출력한다:
   [첫 질문]
   질문 내용

2) 두 번째부터 {TOTAL_QUESTIONS - 1}번째 질문까지는:
   [다음 질문]
   질문 내용

3) {TOTAL_QUESTIONS}번째 질문(마지막)은:
   [마지막 질문]
   마지막 질문 1개만 출력

4) 학생이 답변하면 반드시 아래 형식으로만 답한다:
   [피드백]
   학생 답변 평가 1~2문장

   [다음 질문] 또는 [마지막 질문]
   질문 내용

5) 규칙을 절대 어기지 말 것.
"""

    # 메시지 히스토리
    messages = [
        {"role": "system", "content": system_prompt}
    ]

    # -------------------------------------------------------
    # 첫 질문 요청 (피드백 절대 포함 금지)
    # -------------------------------------------------------
    first_question_prompt = f"""
생기부를 기반으로 첫 번째 질문을 출력하세요.

출력 형식:
[첫 질문]
질문 내용
"""
    messages.append({"role": "user", "content": first_question_prompt})

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=400,
    )

    first_question = resp.choices[0].message.content
    messages.append({"role": "assistant", "content": first_question})

    print("\n===== 🎤 AI 면접관 모드 시작 =====")
    print("종료하려면 exit 또는 quit 입력\n")
    print(first_question)

    # -------------------------------------------------------
    # 2번째 ~ 마지막 질문 루프
    # -------------------------------------------------------
    current_question_number = 2

    while current_question_number <= TOTAL_QUESTIONS:
        answer = input("\n[학생 답변] > ").strip()

        if answer.lower() in ("exit", "quit"):
            print("\n면접 연습을 종료합니다. 수고했어요! 🙌")
            break

        # 마지막 질문 여부 체크
        is_last = (current_question_number == TOTAL_QUESTIONS)

        follow_prompt = f"""
아래 학생의 답변을 평가하세요.

[학생 답변]
{answer}

출력 형식은 반드시 아래 중 하나:

{'[마지막 질문]' if is_last else '[다음 질문]'}

형식:
[피드백]
학생 답변 평가 1~2문장

{'[마지막 질문]' if is_last else '[다음 질문]'}
질문 내용
"""

        messages.append({"role": "user", "content": follow_prompt})

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=600,
        )

        content = resp.choices[0].message.content
        messages.append({"role": "assistant", "content": content})

        print("\n--------------------------------")
        print(content)

        # 마지막 질문 출력했으면 종료
        if is_last:
            print("\n✨ 모든 질문이 끝났습니다. 수고했어요! 🙌")
            break

        current_question_number += 1


if __name__ == "__main__":
    with open("wnskadud_structured (1).json", "r", encoding="utf-8") as f:
        student_json = json.load(f)

    start_ai_interview(student_json)
