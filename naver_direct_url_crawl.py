import requests
import re
from bs4 import BeautifulSoup
import json


name = '노티드도넛'
mapURL='https://map.naver.com/p/search/'+name+'#'
url = "https://pcmap.place.naver.com/place/list?query="+name+"&clientX=126.960025&clientY=37.550192&bounds=126.96711483880233%3B37.55576310863216%3B126.9885081379054%3B37.568775230213575&ts=1699927563647&mapUrl="+mapURL
## 50개만 나오는게 아쉽네 -> 페이지 번호가 url에 안 나오는데 흠..
res = requests.get(url)
res.encoding = 'UTF-8'

soup = BeautifulSoup(res.text, 'html.parser')

# <script> 태그에서 window.__APOLLO_STATE__ 변수를 포함하는 스크립트 찾기
# 이 정규 표현식은 window.__APOLLO_STATE__ 뒤에 오는 JavaScript 객체를 찾습니다
script_text = None
for script in soup.find_all('script'):
    if 'window.__APOLLO_STATE__' in script.text:
        script_text = script.text
        break

# 스크립트 텍스트가 있으면, window.__APOLLO_STATE__ 값을 추출
if script_text:
    match = re.search(r'window\.__APOLLO_STATE__ = ({.*?});', script_text)
    if match:
        apollo_state_json = match.group(1)  # JSON 문자열을 추출합니다.
        # print(apollo_state_json)
    else:
        print("window.__APOLLO_STATE__을 찾을 수 없습니다.")
else:
    print("스크립트 태그에서 window.__APOLLO_STATE__ 변수를 포함하는 부분을 찾을 수 없습니다.")

apollo_state_object = json.loads(apollo_state_json)
dict_key = [x for x in apollo_state_object.keys()]
naver_id = []
for x in dict_key:
    if x.startswith('PlaceSummary:') or x.startswith('RestaurantListSummary:'):
        naver_id.append(x.split(':')[1])
print(len(naver_id))

for id_ in naver_id :
    search_url = 'https://pcmap.place.naver.com/restaurant/'+id_+'/review/visitor?entry=bmp&from=map&fromPanelNum=2&timestamp=202311141037&x=126.95576826566969&y=37.55216566956184&reviewSort=recent'  #최신순 리뷰 주소
    search_res = requests.get(search_url)
    print(search_res.status_code)