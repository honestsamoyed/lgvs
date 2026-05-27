# LG VS LinkedIn Dashboard 2026

LG Vehicle Solution Global LinkedIn 채널 운영 현황 대시보드

---

## 파일 구조

```
lg-vs-linkedin-dashboard/
├── index.html      ← 대시보드 메인 (수정 불필요)
├── posts.json      ← 데이터 파일 (여기만 업데이트하면 됨)
└── README.md
```

---

## GitHub Pages 배포 방법 (5분)

### 1단계 — GitHub 저장소 만들기
1. https://github.com/new 접속
2. Repository name: `lg-vs-linkedin-dashboard`
3. **Public** 선택 (Pages 무료 사용 조건)
4. "Create repository" 클릭

### 2단계 — 파일 업로드
GitHub 저장소 페이지에서:
1. "uploading an existing file" 클릭
2. `index.html`, `posts.json`, `README.md` 3개 파일 드래그 앤 드롭
3. "Commit changes" 클릭

### 3단계 — Pages 활성화
1. 저장소 상단 **Settings** 탭 클릭
2. 왼쪽 메뉴 **Pages** 클릭
3. Source → **Deploy from a branch**
4. Branch → **main** / folder → **/ (root)**
5. **Save** 클릭

### 4단계 — 링크 확인 (약 1~2분 후)
```
https://[GitHub계정명].github.io/lg-vs-linkedin-dashboard/
```

---

## 데이터 업데이트 방법

### 수동 업데이트 (간단)
`posts.json`에서 포스팅 항목 수정 후 GitHub에 재업로드하면 자동 반영됩니다.

**posts.json 필드 설명:**
```json
{
  "no": 1,                    // 월 내 번호
  "month": "Jun",             // Jan|Feb|Mar|Apr|May|Jun|Jul...
  "title": "포스팅 제목",
  "type": "Video",            // Video|IMG|Mention|Newsletter
  "pct": 0.67,                // 완성도 (0~1)
  "status": "In-progress",   // "Completed" | "In-progress" | ""
  "url": "https://...",       // LinkedIn 포스팅 URL (없으면 "")
  "steps": [1,1,1,1,0,0],    // 6단계 체크 (1=완료, 0=미완료)
                              // [기획제안, 제작, 1stDraft, Feedback, 2ndReview, Final]
  "ad": "Sponsored",          // 광고 유형 (없으면 "")
  "nextStep": "다음 할 일"    // In-progress일 때 표시될 메모
}
```

---

## LinkedIn API 자동화 연동 (고급)

LinkedIn Marketing API를 통해 **게시된 포스팅 URL과 상태를 자동으로 가져올 수 있습니다.**

### 필요한 것
- LinkedIn Developer App (https://www.linkedin.com/developers/)
- LG VS Company 페이지 Admin 권한
- `r_organization_social` OAuth 스코프

### GitHub Actions 자동 업데이트 설정

`.github/workflows/update.yml` 파일을 만들어 저장소에 추가하세요:

```yaml
name: Update LinkedIn Data

on:
  schedule:
    - cron: '0 9 * * 1'   # 매주 월요일 오전 9시 (UTC 기준)
  workflow_dispatch:        # 수동 실행 버튼

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Fetch LinkedIn posts
        env:
          LI_TOKEN: ${{ secrets.LINKEDIN_ACCESS_TOKEN }}
          LI_ORG_ID: ${{ secrets.LINKEDIN_ORG_ID }}      # LG VS 페이지 ID
        run: |
          python3 fetch_linkedin.py

      - name: Commit updated data
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add posts.json
          git diff --quiet && git diff --staged --quiet || git commit -m "Auto-update: LinkedIn data $(date +'%Y-%m-%d')"
          git push
```

### LinkedIn 데이터 fetch 스크립트

`fetch_linkedin.py` 파일을 만들어 저장소에 추가하세요:

```python
import os, json, requests
from datetime import datetime

TOKEN = os.environ['LI_TOKEN']
ORG_ID = os.environ['LI_ORG_ID']

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "LinkedIn-Version": "202401",
    "X-Restli-Protocol-Version": "2.0.0"
}

# 조직 포스팅 가져오기
def fetch_posts():
    url = f"https://api.linkedin.com/v2/ugcPosts?q=authors&authors=List(urn:li:organization:{ORG_ID})&count=50"
    r = requests.get(url, headers=headers)
    return r.json().get("elements", [])

def build_posts_json(li_posts):
    """LinkedIn API 응답을 posts.json 형식으로 변환"""
    existing = json.load(open("posts.json")) if os.path.exists("posts.json") else []
    existing_urls = {p["url"]: p for p in existing if p.get("url")}

    result = list(existing)  # 기존 데이터 유지

    for lp in li_posts:
        post_id = lp.get("id", "")
        url = f"https://www.linkedin.com/feed/update/{post_id}"

        if url in existing_urls:
            # URL이 이미 있으면 status만 Completed로 업데이트
            for p in result:
                if p.get("url") == url and p["status"] != "Completed":
                    p["status"] = "Completed"
                    p["pct"] = 1.0
                    p["steps"] = [1,1,1,1,1,1]
        # 완전히 새로운 포스팅은 수동으로 추가 권장 (제목, 타입 정보가 필요)

    return result

posts = fetch_posts()
updated = build_posts_json(posts)
json.dump(updated, open("posts.json","w"), ensure_ascii=False, indent=2)
print(f"Updated: {len(updated)} posts")
```

### GitHub Secrets 등록
저장소 → Settings → Secrets and variables → Actions → New repository secret:
- `LINKEDIN_ACCESS_TOKEN` : LinkedIn API 액세스 토큰
- `LINKEDIN_ORG_ID` : LG VS Company 페이지 ID (숫자)

### LinkedIn 액세스 토큰 발급
1. https://www.linkedin.com/developers/apps → 앱 생성
2. Products 탭 → "Marketing Developer Platform" 신청
3. OAuth 2.0 → `r_organization_social` 스코프 요청
4. 토큰 생성 (유효기간 60일 → 갱신 자동화 별도 필요)

---

## 자동 갱신
대시보드는 열려 있는 동안 **5분마다 posts.json을 자동으로 다시 불러옵니다.**
GitHub Actions로 데이터를 업데이트하면 다음 갱신 시 자동 반영됩니다.
