def interview_prompt(student):
    return f"""
당신은 입시 전문 면접관입니다.  
다음 학생의 생기부 정보를 바탕으로 심층 질문 5개를 만들어주세요.

### 학생 정보
이름: {student.get("name")}
학년: {student.get("grade")}
세부특기사항: {student.get("details")}
수상경력: {student.get("awards")}
동아리 활동: {student.get("club")}
진로희망: {student.get("career_goal")}

### 요구사항
- 실제 교내·대학 면접처럼 깊이 있는 질문
- 학생의 경험을 추적하는 꼬리 질문 포함
- 지식 기반·경험 기반·상황형 질문 혼합
- 너무 길게 말하지 말 것
"""
