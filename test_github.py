# 이 파일을 GitHub 루트에 올리고 Streamlit에서 임시 테스트용으로 실행
# main.py 맨 위에 아래 코드를 임시 추가해서 확인

import streamlit as st
import urllib.request
import json
import base64

st.title("GitHub 연결 테스트")

token = st.secrets.get("GITHUB_TOKEN", "")
repo  = st.secrets.get("GITHUB_REPO", "")

st.write(f"TOKEN 앞 10자: `{token[:10]}...`")
st.write(f"REPO: `{repo}`")

if st.button("data/users.json 읽기 테스트"):
    url = f"https://api.github.com/repos/{repo}/contents/data/users.json"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "zeroda-platform"
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            st.success(f"파일 크기: {data.get('size')} bytes")
            st.write(f"SHA: {data.get('sha','')[:10]}")
            raw = data['content'].replace('\n','').replace(' ','')
            content = base64.b64decode(raw).decode('utf-8')
            rows = json.loads(content)
            st.success(f"행 수: {len(rows)}")
            st.json(rows)
    except urllib.error.HTTPError as e:
        st.error(f"HTTP 오류: {e.code} {e.reason}")
        st.write(e.read().decode())
    except Exception as e:
        st.error(f"오류: {e}")
