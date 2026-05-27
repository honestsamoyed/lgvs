import os
import json
import requests
from datetime import datetime

ACCESS_TOKEN  = os.environ['LI_ACCESS_TOKEN']
REFRESH_TOKEN = os.environ.get('LI_REFRESH_TOKEN', '')
CLIENT_ID     = os.environ.get('LI_CLIENT_ID', '')
CLIENT_SECRET = os.environ.get('LI_CLIENT_SECRET', '')

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "LinkedIn-Version": "202401",
    "X-Restli-Protocol-Version": "2.0.0",
    "Content-Type": "application/json"
}

# ── 1. 토큰 갱신 ────────────────────────────────────────────────
def refresh_access_token():
    """리프레시 토큰으로 새 액세스 토큰 발급"""
    if not all([REFRESH_TOKEN, CLIENT_ID, CLIENT_SECRET]):
        print("Refresh token or client credentials missing — skipping refresh")
        return ACCESS_TOKEN

    r = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "refresh_token",
            "refresh_token": REFRESH_TOKEN,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    if r.status_code == 200:
        new_token = r.json().get("access_token")
        print(f"Token refreshed successfully")
        # GitHub Actions에서 새 토큰을 Secret으로 자동 업데이트하려면
        # gh CLI 또는 GitHub API 호출 필요 (별도 설정)
        return new_token
    else:
        print(f"Token refresh failed: {r.status_code} — using existing token")
        return ACCESS_TOKEN


# ── 2. LG VS Company 페이지 ID 자동 조회 ──────────────────────
def get_org_id():
    """액세스 토큰으로 연결된 조직 ID 조회"""
    r = requests.get(
        "https://api.linkedin.com/v2/organizationAcls?q=roleAssignee&role=ADMINISTRATOR&state=APPROVED",
        headers=HEADERS
    )
    if r.status_code != 200:
        raise Exception(f"Failed to get org list: {r.status_code} {r.text}")

    elements = r.json().get("elements", [])
    if not elements:
        raise Exception("No organizations found for this token")

    # LG VS Company 페이지 찾기
    for el in elements:
        org_urn = el.get("organization", "")
        org_id = org_urn.split(":")[-1]

        # 조직 이름 확인
        org_r = requests.get(
            f"https://api.linkedin.com/v2/organizations/{org_id}",
            headers=HEADERS
        )
        if org_r.status_code == 200:
            name = org_r.json().get("localizedName", "")
            print(f"Found org: {name} (ID: {org_id})")
            if "vehicle" in name.lower() or "vs" in name.lower() or "lg" in name.lower():
                return org_id

    # 첫 번째 조직 사용
    first_id = elements[0].get("organization", "").split(":")[-1]
    print(f"Using first org ID: {first_id}")
    return first_id


# ── 3. 포스팅 가져오기 ─────────────────────────────────────────
def fetch_org_posts(org_id):
    """조직 페이지 포스팅 목록 조회"""
    url = (
        f"https://api.linkedin.com/v2/ugcPosts"
        f"?q=authors&authors=List(urn%3Ali%3Aorganization%3A{org_id})"
        f"&count=50&sortBy=LAST_MODIFIED"
    )
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        print(f"Posts fetch failed: {r.status_code} {r.text}")
        return []

    posts = r.json().get("elements", [])
    print(f"Fetched {len(posts)} posts from LinkedIn")
    return posts


# ── 4. posts.json 병합 ────────────────────────────────────────
def merge_posts(li_posts):
    """LinkedIn 포스팅과 기존 posts.json 병합"""
    existing = []
    if os.path.exists("posts.json"):
        with open("posts.json", "r", encoding="utf-8") as f:
            existing = json.load(f)

    # 기존 URL → 항목 매핑
    url_map = {}
    for p in existing:
        if p.get("url"):
            url_map[p["url"]] = p

    updated_count = 0

    for lp in li_posts:
        post_id = lp.get("id", "")
        if not post_id:
            continue

        # LinkedIn 포스팅 URL 생성
        li_url = f"https://www.linkedin.com/feed/update/{post_id}"
        li_url_alt = f"https://www.linkedin.com/feed/update/{post_id}/"

        # 기존 항목과 매칭
        matched = url_map.get(li_url) or url_map.get(li_url_alt)

        if matched:
            # 이미 Completed가 아닌 경우 → Completed로 업데이트
            if matched.get("status") != "Completed":
                matched["status"] = "Completed"
                matched["pct"] = 1.0
                matched["steps"] = [1, 1, 1, 1, 1, 1]
                matched["nextStep"] = ""
                updated_count += 1
                print(f"Updated to Completed: {matched.get('title', post_id)}")

    print(f"Updated {updated_count} posts to Completed")
    return existing


# ── 5. 실행 ──────────────────────────────────────────────────
def main():
    print(f"Starting LinkedIn data sync — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # 토큰 갱신 시도
    token = refresh_access_token()
    if token != ACCESS_TOKEN:
        HEADERS["Authorization"] = f"Bearer {token}"

    # 조직 ID 조회
    try:
        org_id = get_org_id()
    except Exception as e:
        print(f"Error getting org ID: {e}")
        return

    # 포스팅 가져오기
    li_posts = fetch_org_posts(org_id)
    if not li_posts:
        print("No posts fetched — keeping existing data")
        return

    # 병합 및 저장
    merged = merge_posts(li_posts)
    with open("posts.json", "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"Done — posts.json updated with {len(merged)} total entries")


if __name__ == "__main__":
    main()
