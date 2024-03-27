### ver1012
### 이전에 빠졌던 베이커리와 에러가 떴던 애들을 (괄호에 있는 내용 삭제한 후) 로컬에서 크롤링


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver import ActionChains
from tqdm import tqdm
import pickle, time, requests, secrets, string
import concurrent.futures
import boto3
from boto3.dynamodb.conditions import Key
from absl import app, flags
from io import BytesIO
from PIL import Image

FLAGS = flags.FLAGS

flags.DEFINE_integer("start", 0, '')
flags.DEFINE_integer("end", 0, '')
flags.DEFINE_string("access_key", 'data', '')
flags.DEFINE_string("secret_access_key", 'data', '')
Image.MAX_IMAGE_PIXELS = None

def generate_secure_random_string(length):
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def c_gen(driver, module_str, xpath, *args):
    if len(args)>0:
        try:
            return c_gen(driver, module_str, xpath)
        except:
            return ''
    else:
        state_str = module_str[0]
        if state_str == 'W': # 1초 기다려서 나오면 찾고, 없으면 패스
            wait = WebDriverWait(driver, 1)
            focus = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        elif state_str == 'L': # 5초 기다리기
            wait = WebDriverWait(driver, 5)
            focus = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        elif state_str == 'X': # 해당 xpath에 포커스 두기
            focus = driver.find_element(By.XPATH, xpath)
        elif state_str == 'I': # 해당 ID에 포커스 두기
            focus = driver.find_element(By.ID, xpath)
        elif state_str == 'i': # 해당 ID 3초 기다리기
            wait = WebDriverWait(driver, 3)
            focus = wait.until(EC.presence_of_element_located((By.ID, xpath)))
        elif state_str == 'C': # 해당 Class 나타날 때까지 최대 3초 기다린 후에 포커스 두기
            wait = WebDriverWait(driver, 3)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, xpath)))
            focus = driver.find_element(By.CLASS_NAME, xpath)
        elif state_str == 'c': # 해당 Class 3초 기다리기
            wait = WebDriverWait(driver, 3)
            focus = wait.until(EC.presence_of_element_located((By.CLASS_NAME, xpath)))
        elif state_str == 'G': # 해당 url로 이동
            driver.get(xpath)
            return 0
        elif state_str == 'D': # frame을 디폴트 frame으로 돌림
            driver.switch_to.default_content()
            return 0
        elif state_str == 'M': # 다중 class 선택
            focus = driver.find_elements(By.CLASS_NAME, xpath)

        elem_str = module_str[1]
        if elem_str == 'F': # 프레임 변경
            driver.switch_to.frame(focus)
        elif elem_str == 'C': # 클릭
            focus.click()
        elif elem_str == 'c': # 다중 클릭
            action = ActionChains(driver)
            action.move_to_element(focus[0]).perform()
            for x in focus:
                try:
                    x.click()
                except:
                    pass
        elif elem_str == 'T': # 텍스트 리턴
            return focus.text
        elif elem_str == 't': # 다중 텍스트 리턴
            return [x.text for x in focus]
        elif elem_str == '_': # focus 주소 리스트 리턴
            return focus
        elif elem_str == 'M': # 메뉴찾아서 누르기
            action = ActionChains(driver)
            action.move_to_element(focus[0]).perform()
            for x in focus:
                if x.text == '메뉴':
                    x.click()
                    break
                else:
                    pass
        elif elem_str == 'R': # 리뷰찾아서 누르기
            action = ActionChains(driver)
            action.move_to_element(focus[0]).perform()
            for x in focus:
                if x.text == '리뷰':
                    x.click()
                    break
                else:
                    pass

def c_try(driver, module_str, xpaths):
    for xpath in xpaths:
        try:
            c_gen(driver, module_str, xpath)
        except:
            pass
        
def c_try_2(driver, module_str, xpaths):  # xpaths에 두 개 넣어서 검색 후 텍스트 긁기 (module_str='Mt' only)
    li = []
    for xpath in xpaths:
        try:
            li.append(c_gen(driver, module_str, xpath))
        except:
            pass
    return li[0]+li[1]

def crawling(driver, category_naver, query_str, table_rest, table_rest_error, table_temp, table_temp_check, table_rest_review_error, table_rest_menu_error,  titleloc, s3):  #titleloc : ('식당명', '위치')
    try:
        c_gen(driver, 'D', '')
        time.sleep(0.6)
        c_gen(driver, 'iF', 'entryIframe')  
        c_data = {}
        object_key = generate_secure_random_string(16)
        c_data['obj_key'] = object_key
        c_data['loc'] = titleloc[1]
        c_data['title'] = c_gen(driver, 'CT', 'Fc1rA')
        c_data['category'] = c_gen(driver, 'CT', 'DJJvD')
        standard = c_data['title'].strip()+c_data['category'].strip()   ### searchIframe에 카테고리가 없는 경우도 있어서 이름만 비교
    
        errorloc = '당겨져들어가는 이슈'
        ## 너무 빨리 크롤링이 돼서 식당명이 이전 껄로 당겨져서 들어가는 이슈 해결
        ## titleloc = [name, loc] in searchIframe
        if '\n' in titleloc[0]:   #중간에 네이버결제 이런 거 주렁주렁 달려있는 케이스
            ############################# x[0]에 카테고리가 같이 긁히는 경우 있음   --> c_data['title']에는 카테고리 안 긁힘
            compare = titleloc[0].split('\n')
            sf = compare[0].strip()     #이름(+카테고리)
        else:
            sf = titleloc[0].strip()   #이름(+카테고리)
        perhaps_start = time.time()
        while (sf != standard[:len(sf)]):
            c_data['title'] = c_gen(driver, 'CT', 'Fc1rA')
            c_data['category'] = c_gen(driver, 'CT', 'DJJvD')
            standard = str(c_data['title']).strip()+str(c_data['category']).strip()
            perhaps_end = time.time()
            if (perhaps_end - perhaps_start > 20):   #title과 category를 합친 문자열이 같아질때까지 계속 : entryIframe이 늦게떠서 데이터가 밀려들어가는 이슈 해결
                print('sf: ', sf, 'standard:', standard[:len(sf)], 'full_standard: ', standard)
                table_rest_error.put_item(Item={'title': sf, 'loc': titleloc[1]})
                c_gen(driver, 'D', '')
                c_gen(driver, 'iF', 'searchIframe')
                return
        
        ###### category_naver에 없는, 식당 아닌 장소라면 바로 종료 후 다음 식당
        if c_data['category'] not in category_naver:
            c_gen(driver, 'D', '')
            c_gen(driver, 'iF', 'searchIframe')
            return
        
        errorloc = '리뷰 숫자 긁기'
        try:
            c_data['review_num'] = c_gen(driver, 'Mt', 'PXMot')
        except:
            pass

        errorloc = '기본 정보 긁기'
        try:
            c_data['degree'] = c_gen(driver, 'CT', 'RHB01', '')
        except:
            pass
        try:
            c_gen(driver, 'CC', 'y6tNq', '')  # 영업시간 toggle 열기위해 포커스 두고 클릭  -> 영업시간은 한 번 클릭하면 y6tNq가 하나 더 생겨서 그걸 또 누르면 다시 닫힘
        except:
            pass

        try:
            c_gen(driver, 'Mc', 'zPfVt', '')  # 식당설명 toggle 열기위해 포커스 두고 클릭 
        except:
            pass
        ### 길찾기도 span class='zPfVt'라서 그렇구만....
        try:
            c_data['info'] = c_gen(driver, 'Mt', 'O8qbU')   #열어두고 한 번에 크롤링
        except:
            pass
        errorloc = '리뷰 긁기'
        ### 리뷰 긁기
        try:
            c_gen(driver, 'MR', 'veBoZ')      # 리뷰 탭으로 이동
            time.sleep(1)
            c_gen(driver, 'Mc', 'mSdTM', '')     # 리뷰 최신순 클릭

            review_end = False
            start = time.time()
            ic = time.time()
            while not review_end:
                if ic - start > 600:       ### 리뷰 더보기를 600초 누르기 => 리뷰 추천순 240개만 갖고왔던 이슈 해결 : 600초는 추천순 5000개 넘게 긁어올 수 있는 시간
                    break
                try:
                    c_gen(driver, 'CC', 'fvwqf')   # 리뷰 탭의 더보기 있으면 다 누르기
                    ic = time.time()
                except: # while문 탈출
                    review_end = True

            c_gen(driver, 'Mc', 'zPfVt', '')  # 각 리뷰 toggle 열기 위해 모두 클릭   
            # c_gen(driver, 'Mc', 'P1zUJ.ZGKcF')  #각 리뷰 반응키워드 toggle 열기  반응키워드는 bert, llm에서 오히려 못 잡음

            recheck = table_temp.query(KeyConditionExpression=Key('titlelocation').eq(str(c_data['title'] + c_data['loc'])))
            recheck2 = table_temp_check.query(KeyConditionExpression=Key('titlelocation').eq(str(c_data['title'] + c_data['loc'])))
            if (recheck['Count']==0) and (recheck2['Count']==0):
                c_data['review'] = c_gen(driver, 'Mt', 'YeINN')
                imgs = driver.find_elements(By.CSS_SELECTOR, ".K0PDV._img.fKa0W")
                img_num = min(len(imgs), 24)
                for i in range(img_num):
                    errorloc = '이미지 저장'
                    style_attribute = imgs[i].get_attribute("style")
                    background_image_url = None
                    style_parts = style_attribute.split(';')
                    for part in style_parts:
                        if "background-image" in part:
                            background_image_url = part.split("src=")[1].split(".jpeg")[0]
                    img_url = background_image_url.replace('%3A', ':').replace("%2F", '/')
                    download = requests.get(img_url)
                    img_data = download.content
                    img_file = Image.open(BytesIO(img_data))
                    # 썸네일 생성 (크기 조절)
                    max_thumbnail_size = (1600, 1600)
                    img_file.thumbnail(max_thumbnail_size)
                    # BytesIO로 변환
                    img_file_byte_io = BytesIO()
                    img_file.save(img_file_byte_io, format='JPEG')
                    img_file_byte_io.seek(0)
                    s3.upload_fileobj(img_file_byte_io, 'whatever-img-seoul', object_key + '_' + str(i)+ '.jpeg')
            else:
                c_gen(driver, 'D', '')
                c_gen(driver, 'iF', 'searchIframe')
                return 
        except:
            if len(c_data['review'])>400:
                temp_ = c_data.copy()
                c_data_first = temp_.copy()
                c_data_first['review'] = c_data['review'][:400]
                table_rest_review_error.put_item(Item=c_data)
                for num in range(len(c_data['review'])//400):
                    split_c_data = temp_.copy()
                    split_c_data['title'] = c_data['title']+'_'+ str(num+2)
                    split_c_data['review'] = c_data['review'][(num+1)*400:(num+2)*400]
                    table_rest_review_error.put_item(Item=c_data)
            else:
                table_rest_review_error.put_item(Item=c_data)
            c_gen(driver, 'D', '')
            c_gen(driver, 'iF', 'searchIframe')
            return 
        
        if len(c_data['review'])==0:
            table_rest_review_error.put_item(Item=c_data)  
            c_gen(driver, 'D', '')
            c_gen(driver, 'iF', 'searchIframe')
            return
        
        errorloc = '메뉴 긁기'
        #### 여기서 메뉴 못 긁어도 오류가 발생하는 건 아니고 E2jtL과 info_detail이 없어서 바로 put_item으로 가는거구나. 그럼 len(c_data['menu']로 접근)
        c_gen(driver, 'MM', 'veBoZ')      # 메뉴 탭으로 이동
        try:
            c_gen(driver, 'CC', 'fvwqf', '')  # 메뉴 탭에서 더보기 누르기      ###### 네이버주문이면 이게 없어서 그러네    
            c_data['menu'] = c_try_2(driver, 'Mt', ['E2jtL', 'info_detail'])  # 메뉴 정보 크롤링
            if len(c_data['menu'])==0:
                if len(c_data['review'])>400:   # 만약 review가 1000개라서 못 들어가는데 menu_error에 넣으려고 했다면 에러 발생
                    raise InterruptedError
                else:
                    table_rest_menu_error.put_item(Item=c_data)
        except:
            if len(c_data['review'])>400:   # 만약 review가 1000개라서 못 들어가는데 menu_error에 넣으려고 했다면 에러 발생
                temp_ = c_data.copy()
                c_data_first = temp_.copy()
                c_data_first['review'] = c_data['review'][:400]
                table_rest_menu_error.put_item(Item=c_data_first)   
                for num in range(len(c_data['review'])//400):
                    split_c_data = temp_.copy()
                    split_c_data['title'] = c_data['title']+'_'+ str(num+2)
                    split_c_data['review'] = c_data['review'][(num+1)*400:(num+2)*400]
                    table_rest_menu_error.put_item(Item=split_c_data)   
            else:
                table_rest_menu_error.put_item(Item=c_data)   
            c_gen(driver, 'D', '')
            c_gen(driver, 'iF', 'searchIframe')
            return

        ### 리뷰가 많으면 분할해서 dynamoDB에 넣기 - dynamoDB의 최대 put item size가 400kb
        print(len(c_data['review']))
        recheck = table_temp.query(KeyConditionExpression=Key('titlelocation').eq(str(c_data['title'] + c_data['loc'])))
        recheck2 = table_temp_check.query(KeyConditionExpression=Key('titlelocation').eq(str(c_data['title'] + c_data['loc'])))
        if (recheck['Count']==0) and (recheck2['Count']==0):
            if len(c_data['review'])>400:
                temp_ = c_data.copy()
                c_data_first = temp_.copy()
                c_data_first['review'] = c_data['review'][:400]
                table_temp.put_item(Item={'titlelocation':c_data_first['title']+c_data_first['loc'], 'obj_key':c_data_first['obj_key']}) # 크롤링이 끝까지 다 된 애들만 temp에도 업로드
                table_temp_check.put_item(Item={'titlelocation':c_data_first['title']+c_data_first['loc'], 'obj_key':c_data_first['obj_key']}) # 크롤링이 끝까지 다 된 애들만 temp에도 업로드
                table_rest.put_item(Item=c_data_first)

                for num in range(len(c_data['review'])//400):
                    split_c_data = temp_.copy()
                    split_c_data['title'] = c_data['title']+'_'+ str(num+2)
                    split_c_data['review'] = c_data['review'][(num+1)*400:(num+2)*400]
                    table_temp.put_item(Item={'titlelocation':split_c_data['title']+split_c_data['loc'], 'obj_key':split_c_data['obj_key']}) # 크롤링이 끝까지 다 된 애들만 temp에도 업로드
                    table_temp_check.put_item(Item={'titlelocation':split_c_data['title']+split_c_data['loc'], 'obj_key':split_c_data['obj_key']}) # 크롤링이 끝까지 다 된 애들만 temp에도 업로드
                    table_rest.put_item(Item=split_c_data)
            else:
                table_temp.put_item(Item={'titlelocation':c_data['title']+c_data['loc'], 'obj_key':c_data['obj_key']}) # 크롤링이 끝까지 다 된 애들만 temp에도 업로드
                table_temp_check.put_item(Item={'titlelocation':c_data['title']+c_data['loc'], 'obj_key':c_data['obj_key']}) # 크롤링이 끝까지 다 된 애들만 temp에도 업로드
                table_rest.put_item(Item=c_data)
        else:
            c_gen(driver, 'D', '')   
            c_gen(driver, 'iF', 'searchIframe')
            return

        key = {'title': c_data['title'], 'loc':c_data['loc']}
        # error, menu_error, review_error DB로 넘어간 애들 중에 이번에 돌려서 제대로 돌아갔으면 error DB에서 삭제
        resp_error = table_rest_error.query(KeyConditionExpression=Key('title').eq(c_data['title'])&Key('loc').eq(c_data['loc']))  #입구컷 당한 애들은 loc이 no loc이긴 함..
        resp_menu_error = table_rest_menu_error.query(KeyConditionExpression=Key('title').eq(c_data['title'])&Key('loc').eq(c_data['loc']))
        resp_review_error = table_rest_review_error.query(KeyConditionExpression=Key('title').eq(c_data['title'])&Key('loc').eq(c_data['loc']))
        if resp_error['Count']>0: # if 있으면 -> 삭제
            table_rest_error.delete_item(Key=key)
        if resp_menu_error['Count']>0: # if 있으면 -> 삭제
            table_rest_menu_error.delete_item(Key=key)
        if resp_review_error['Count']>0: # if 있으면 -> 삭제
            table_rest_review_error.delete_item(Key=key) 
        for num in range(2,10):
            resp_error = table_rest_error.query(KeyConditionExpression=Key('title').eq(c_data['title']+'_'+str(num))&Key('loc').eq(c_data['loc']))  #입구컷 당한 애들은 loc이 no loc이긴 함..
            resp_menu_error = table_rest_menu_error.query(KeyConditionExpression=Key('title').eq(c_data['title']+'_'+str(num))&Key('loc').eq(c_data['loc']))
            resp_review_error = table_rest_review_error.query(KeyConditionExpression=Key('title').eq(c_data['title']+'_'+str(num))&Key('loc').eq(c_data['loc']))
            key = {'title': c_data['title']+'_'+str(num), 'loc':c_data['loc']}
            if resp_error['Count']>0: # if 있으면 -> 삭제
                table_rest_error.delete_item(Key=key)
            if resp_menu_error['Count']>0: # if 있으면 -> 삭제
                table_rest_menu_error.delete_item(Key=key)
            if resp_review_error['Count']>0: # if 있으면 -> 삭제
                table_rest_review_error.delete_item(Key=key) 
        c_gen(driver, 'D', '')
        c_gen(driver, 'iF', 'searchIframe')

    except Exception as e:
        try: 
            cross_check = table_rest.query(KeyConditionExpression=Key('obj_key').eq(c_data['obj_key'])&Key('title').eq(c_data['title']))
            if cross_check['Count']==0:
                if len(c_data['review'])>400:   # 만약 review가 1000개라서 못 들어가는데 menu_error에 넣으려고 했다면 에러 발생
                    temp_ = c_data.copy()
                    c_data_first = temp_.copy()
                    c_data_first['review'] = c_data['review'][:400]
                    table_rest_error.put_item(Item=c_data_first)
                    for num in range(len(c_data['review'])//400):
                        split_c_data = temp_.copy()
                        split_c_data['title'] = c_data['title']+'_'+ str(num+2)
                        split_c_data['review'] = c_data['review'][(num+1)*400:(num+2)*400]
                        table_rest_error.put_item(Item=split_c_data)
                else:
                    table_rest_error.put_item(Item=c_data)   
                
        except:
            try:
                if len(c_data['title'])>0:
                    if len(c_data['review'])>400:   # 만약 review가 1000개라서 못 들어가는데 menu_error에 넣으려고 했다면 에러 발생
                        temp_ = c_data.copy()
                        c_data_first = temp_.copy()
                        c_data_first['review'] = c_data['review'][:400]
                        table_rest_error.put_item(Item=c_data_first)
                        for num in range(len(c_data['review'])//400):
                            split_c_data = temp_.copy()
                            split_c_data['title'] = c_data['title']+'_'+ str(num+2)
                            split_c_data['review'] = c_data['review'][(num+1)*400:(num+2)*400]
                            table_rest_error.put_item(Item=split_c_data)
                    else:
                        table_rest_error.put_item(Item=c_data)   
                else:
                    table_rest_error.put_item(Item={'title':query_str, 'loc':'during crawling'})
            except:
                table_rest_error.put_item(Item={'title':query_str, 'loc':'during crawling'})
        c_gen(driver, 'D', '')   
        c_gen(driver, 'iF', 'searchIframe')

def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument('--hide-scrollbars')
    chrome_options.add_argument('--window-size=1280x1696')
    chrome_options.add_argument('--enable-logging')
    chrome_options.add_argument('--log-level=0')
    chrome_options.add_argument('--v=99')
    chrome_options.add_argument('--vmodule')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--single-process')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36')
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-setuid-sandbox")

    # service = Service(executable_path="/snap/bin/chromium.chromedriver")  # aws환경
    service = Service(executable_path="/Users/kalvin/chromedriver_mac_arm64/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    time.sleep(1)
    return driver

def multi(data):
    with open('./category_naver_map.pkl', 'rb') as g:
        category_naver = pickle.load(g)

    driver = create_driver()

    dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-2',
                            aws_access_key_id='aws_access_key_id',
                            aws_secret_access_key='aws_secret_access_key')
    table_rest = dynamodb.Table('table1')  # 크롤링 성공한 애들
    table_temp = dynamodb.Table('table1')
    table_temp_check = dynamodb.Table('table2')  # 기존에 쌓아둔 애들이랑 겹치면 안 되니까! 
    table_rest_review_error = dynamodb.Table('table3') 
    table_rest_menu_error = dynamodb.Table('table4') 
    table_rest_error = dynamodb.Table('table5')
    s3 = boto3.client('s3', region_name='ap-northeast-2', aws_access_key_id='aws_access_key_id', aws_secret_access_key='aws_secret_access_key')
    for ind_cache, item in tqdm(enumerate(data)): 
        try:
            query_str = str(item)
            print(query_str)
            must_see = []
            try:
                c_gen(driver, 'G', "https://map.naver.com/v5/search/" + query_str)
                c_gen(driver, 'D', '')        
                c_gen(driver, 'iF', 'searchIframe')
                driver.find_element(By.CLASS_NAME, 'Ryr1F')
            except:
                table_rest_error.put_item(Item={'title':query_str, 'loc':'not at all'})
                continue

        ### searchIframe에 있는 명단을 전체 다 긁어서 빠지는 명단 없도록 하는 로직
            name = []
            try:
                while True: # searchIframe에서 바로 전체목록이 뜨는 게 아니라 처음엔 한 페이지에 10개만 보여주다가 스크롤 다운하면 더 보여줌
                    scroll = driver.find_element(By.CLASS_NAME, 'Ryr1F')
                    driver.execute_script("arguments[0].scrollBy(0,1000000)", scroll)
                    name_updated = c_try_2(driver, 'Mt', ['place_bluelink.TYaxT', 'place_bluelink.YwYLL']) # 카테고리뺴고 가게명만 긁기
                    if len(name_updated) == len(name):
                        break
                    name = name_updated
            except:
                table_rest_error.put_item(Item={'title':query_str, 'loc':'not at all'})
                continue

            loc = c_try_2(driver, 'Mt', ['rDx68', 'PluMY'])
    ##### searchIframe에서 서울에 있는 식당만 고르기
            combin = [x for x in zip(name, loc)]
            for ind, x in enumerate(combin):  # 비교DB에 쿼리해서 있는지 확인 = 이미 잘 긁어온 식당인지 확인
                if str(x[1]).startswith('서울'):   # 이렇게 해야 search_focus의 index와 똑같아짐
                    pass
                else:
                    continue
                try:
                    if '\n' in x[0]:   #중간에 네이버결제 이런 거 주렁주렁 달려있는 케이스
                        ############################# x[0]에 카테고리가 같이 긁히는 경우 있음
                        compare = x[0].split('\n')
                        sf = compare[0].strip()    #이름
                    else:
                        sf = x[0].strip()   #이름
                        
                    ### error_DB에만 있거나 아예 처음 돌려지는 가게들만 크롤링
                    response = table_temp.query(KeyConditionExpression=Key('titlelocation').eq(str(sf + x[1]))) # 기존 DB에서 확인
                    response_0 = table_temp_check.query(KeyConditionExpression=Key('titlelocation').eq(str(sf + x[1]))) # 새로 저장한 DB에서 확인
                    response_1 = table_rest_review_error.query(KeyConditionExpression=Key('title').eq(sf)&Key('loc').eq(x[1]))
                    response_2 = table_rest_menu_error.query(KeyConditionExpression=Key('title').eq(sf)&Key('loc').eq(x[1]))
                    print(response['Count'], response_0['Count'], response_1['Count'], response_2['Count'])
                    if response['Count']>0:
                        continue
                    elif response_0['Count']>0: # if 있으면 -> 건너뛰기
                        continue
                    elif response_1['Count']>0:
                        continue
                    elif response_2['Count']>0:
                        continue
                    else:  # if 없으면 -> ind 저장하고 제대로 크롤링된 이후에 비교DB에 추가
                        must_see.append([ind,x])
                except:  # 여기로 빠지는 경우는 없었음
                    table_rest_error.put_item(Item={'title':x[0], 'loc':x[1]})
            try: 
                search_focus = c_try_2(driver, 'M_', ['N_KDL', 'C6RjW'])
                if len(must_see)==0: # must_see에 포함된게 없다 = temp에서 모두 다 걸러졌다
                    pass  # continue해도 되지만 driver.quit을 위해 pass
                elif len(must_see)>=1:
                    action = ActionChains(driver)
                    action.move_to_element(search_focus[must_see[0][0]]).perform()
                    for k in must_see: # query_str으로 검색하고 저장한ind에 대해서만 클릭
                        search_focus[k[0]].click()  #### 바로 entryIframe으로 넘어갔다면 여기서 클릭 못하고 뻑남. 여기서 except로 빠짐
                        crawling(driver, category_naver, query_str, table_rest, table_rest_error, table_temp, table_temp_check, table_rest_review_error, table_rest_menu_error, k[1], s3)  #k[1] : ('식당명', '위치')

            except:  ### 바로 알아서 entryIframe으로 넘어가는 애들. k[1]을 여기에도 넣어도 될 듯 한데???
                crawling(driver, category_naver, query_str, table_rest, table_rest_error, table_temp, table_temp_check, table_rest_review_error, table_rest_menu_error, k[1], s3)
            if (ind_cache + 1)%8 == 0:
                driver.quit()
                driver = create_driver()
        except:
            table_rest_error.put_item(Item={'title':query_str, 'loc':'not at all'})
    driver.quit()

def main(argv):
    print('begin...')
    # with open('./seoul_crawl/seoul_rest_name.pkl', 'rb') as g:
    with open('./bakery_and_error_seoul_list.pkl', 'rb') as g:
        rest_name_list = pickle.load(g)

    rest_name = rest_name_list[FLAGS.start:FLAGS.end]
    cpu = 2
    chunk_size = len(rest_name) // cpu
    remainder = len(rest_name) - chunk_size * cpu 
    candidate = [rest_name[i:i + chunk_size] for i in range(0, chunk_size * cpu, chunk_size)]
    for j in range(remainder):
        candidate[j].append(rest_name[chunk_size*cpu + j])
    processes = []

    start = time.time()

    pool = concurrent.futures.ProcessPoolExecutor(max_workers=cpu) 
    for i in range(cpu):
        print(len(candidate[i]))
        feed = candidate[i]
        processes.append(pool.submit(multi, feed))    
    
    concurrent.futures.wait(processes)

    end = time.time()

    print('ALL DONE')
    print('소요시간: ', end-start)

if __name__ == '__main__':
    app.run(main)
