import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np
import faiss, math, copy, itertools, random, pickle, string, json
from collections import Counter
import pandas as pd
import itertools
from itertools import islice
from flask import Flask, request, jsonify
from pyngrok import conf, ngrok
from flask_cors import CORS
from google.cloud import firestore
from google.oauth2 import service_account
from collections import Counter
from func import *
from nreview_func import *


app = Flask(__name__)
CORS(app)

conf.get_default().region = "ap"
conf.get_default().auth_token = "ngrok" # ngrok token  
http_tunnel = ngrok.connect(9800) # ngrok 시작 및 Port 번호 전달
tunnels = ngrok.get_tunnels() # ngrok forwording 정보

for kk in tunnels: # Forwording 정보 출력
    print(kk)

@app.route('/')  # 기본 경로에 대한 요청 처리 - 파일 다운로드
def load_data():
    pd.options.mode.chained_assignment = None
    with open('long_bads_1106.pkl', 'rb') as f:
        long_bads_1106 = pickle.load(f)
    long_bads = long_bads_1106[long_bads_1106['updated_pred_label']==0].copy() ## 1106에 업데이트된 부정리뷰만 모아놓은 것

    with open('positive_top5.pkl', 'rb') as f:
        df_top = pickle.load(f)

    with open('config.json') as f:
        conf = json.load(f)
    with open('naver_ppd_4.pkl', 'rb') as f:
        df = pickle.load(f)
    with open('obj_key2ind.pkl', 'rb') as f:
        obj_key2ind = pickle.load(f)
    with open('posneg_ratio_dict.pkl', 'rb') as f:
        ratio_dict = pickle.load(f)

    df_loc = [[float(elem['geolocation'][1])*math.cos(math.radians(37)), float(elem['geolocation'][2])] for elem in df]
    obj_key = [elem['obj_key'] for elem in df]  #여기서 바로 title 안 찾는 이유는 title이 겹칠수도 있으니.
    menu_squeeze = [elem['menu_squeeze'] for elem in df]  ### 메뉴가 없으면 제외시키기 위함

    # embed_sample = []
    # for i in range(len(df)):
    #     embed_sample.append('/'.join(''.join(''.join(''.join('/'.join([x[0] for x in df[i]['menu_squeeze']]).split('popularrepresentation')).split('representation')).split('popular')).lower().split('n/')).strip())
    with open('ada-embedded_multi.pkl', 'rb') as f:
        embedded = pickle.load(f)
    embedded = np.array(embedded)
    embedded_pd = pd.DataFrame(embedded)
    with open('ada-embedded_multi_ind.pkl', 'rb') as f:
        embedded_ind = pickle.load(f)
    return conf, df, obj_key2ind, ratio_dict, embedded, embedded_pd, embedded_ind, long_bads, df_top, df_loc, obj_key, menu_squeeze
    # return conf, df, obj_key2ind, ratio_dict, embed_sample, embedded, embedded_pd, embedded_ind

app.config['conf'], app.config['df'], app.config['obj_key2ind'],app.config['ratio_dict'],app.config['embedded'],app.config['embedded_pd'], app.config['embedded_ind'], app.config['long_bads'], app.config['df_top'], app.config['df_loc'], app.config['obj_key'], app.config['menu_squeeze'] = load_data()


############################################################
#####################   N - REVIEW   #######################
############################################################
@app.route('/process_keyword', methods=['POST']) # oopy에서 여기로 콜 쏠 예정. 
def process_keyword():
    long_bads = app.config['long_bads']
    # POST 요청에서 'keyword' 값을 받아옴
    request_data = request.form.get('body')
    keyword = request_data

    # test_func 함수를 통과시켜 결과 값을 얻음
    result = find_nreview(long_bads, keyword)

    # 결과를 JSON 형식으로 반환
    # return jsonify({'result': result}), 200
    return result, 200

@app.route('/process_keyword2', methods=['POST']) # oopy에서 여기로 콜 쏠 예정. 
def process_keyword2():
    long_bads = app.config['long_bads']
    df = app.config['df_top']
 
    df['squeezed_title'] = df['title'].apply(lambda x: x.replace(' ', ''))
    # POST 요청에서 'keyword' 값을 받아옴
    req = request.get_json()
    text_ck = req['userRequest']['utterance']
    result = '정보를 찾을 수 없습니다.'

    # test_func 함수를 통과시켜 결과 값을 얻음
    result = find_nreview2(long_bads, df, text_ck)
    return result, 200



############################################################
####################   HAM - ENGINE   ######################
############################################################
@app.route('/ham_engine', methods=['POST'])  # 기본 경로에 대한 요청 처리
def ham_main():
    conf = app.config['conf']
    df = app.config['df']

    obj_key2ind = app.config['obj_key2ind']
    ratio_dict = app.config['ratio_dict']
    embedded = app.config['embedded']
    embedded_pd = app.config['embedded_pd']
    embedded_ind = app.config['embedded_ind']
    df_loc = app.config['df_loc']
    obj_key = app.config['obj_key']
    menu_squeeze = app.config['menu_squeeze']


    credentials = service_account.Credentials.from_service_account_file(conf['firebase_key'])
    db = firestore.Client(credentials=credentials)

    print(request.get_json())
    room_ID = request.get_json()['body']
    doc_ref = db.collection('HAMRoom').document(room_ID)
    doc = doc_ref.get()
    if doc.exists:
        user_choice = doc.to_dict().get('userFavorRests')
        specific_place = dict()
        num_of_choice_each = []
        for ID in user_choice:
            tmp_place = []
            doc_ref_user = db.collection('Users').document(ID)
            # 문서 가져오기
            doc = doc_ref_user.get()
            if doc.exists:
                # 'markRests' 필드 값 가져오기
                for chosen in user_choice[ID]:
                    mark_rests = doc.to_dict().get('markRests')
                    tmp_place += mark_rests[chosen]
            specific_place[ID] = tmp_place
            num_of_choice_each.append(len(tmp_place))
 
    user_input_obj_key = [item for sublist in specific_place.values() for item in sublist] 
    user_input_ind = [obj_key2ind[x] for x in user_input_obj_key] 
    user_input_ind_unique = np.unique(user_input_ind)
    if len(user_input_ind_unique)==0:
        return '식당을 더 추가해주세요!'
    
    user_loc = [[float(df[elem]['geolocation'][1]), float(df[elem]['geolocation'][2])] for elem in user_input_ind_unique]
    normalized_loc = [[elem[0]*math.cos(math.radians(37)), elem[1]] for elem in user_loc]
    print('normalized_loc', len(normalized_loc))
    treasures = get_circles(normalized_loc, 1/len(normalized_loc), conf['min_score_decay_thold'], conf['min_elem_decay_thold'])

    print('treasures', len(treasures))
    satisfied_loc_cond = []
    for center in treasures:
        x_cen, y_cen = center[0]
        r_cen = center[1]
        for ind, coord in enumerate(df_loc):
            x_coord, y_coord = coord
            if ((x_coord-x_cen)*math.cos(math.radians(y_cen)))**2+(y_coord-y_cen)**2 <= r_cen**2:
                if len(menu_squeeze[ind])!=0:   ### 메뉴가 없으면 제외시킴
                    satisfied_loc_cond.append(obj_key[ind])
    satisfied_loc_cond = np.unique(satisfied_loc_cond)

    print('satisfied_loc_cond', len(satisfied_loc_cond))

    popul_ind = [obj_key2ind[x] for x in satisfied_loc_cond]
    popul_obj_key = [df[i]['obj_key'] for i in popul_ind]

    print('obj_key_length', len(popul_obj_key))

    popul_posneg = []
    popul_posneg_ind = []
    for key_ind, keyword in enumerate(popul_obj_key):
        try:
            pn_ratio = ratio_dict[keyword]
            if pn_ratio > conf['pn_ratio_thrsold']:
                popul_posneg.append(pn_ratio)
                popul_posneg_ind.append(key_ind)
        except Exception as e:
            pass

    satisfied_db_indexing = [popul_ind[i] for i in popul_posneg_ind]
    faiss_db = [embedded[indexing(j, embedded_ind=embedded_ind)] for j in satisfied_db_indexing]

    print('satisfied_db_indexing', len(satisfied_db_indexing))

    d = embedded_pd.shape[1]  # 벡터의 차원
    nb = embedded_pd.shape[0]  # 데이터베이스 크기
    np.random.seed(18)
    db_vectors = np.array(faiss_db).astype('float32')

    print('db_shape', db_vectors.shape)

    # 인덱스 생성
    index11 = faiss.IndexFlatL2(d)  # L2을 사용한 인덱스 생성
    index11.add(db_vectors)

    k = conf["num_of_searching_neighbors"]  # 찾고자 하는 이웃의 수
    query_vectors = np.array([embedded[indexing(x, embedded_ind=embedded_ind)] for x in user_input_ind]).astype('float32')
    D, I = index11.search(query_vectors, k)

    faiss_res_in_df_ind = [satisfied_db_indexing[x] for x in I.reshape(-1)]
    faiss_res_in_df_ind = np.unique(faiss_res_in_df_ind)

    I_in_df_ind = np.array([satisfied_db_indexing[x] for x in I[:,0]])

######## 이 한 줄이 4.2초 걸림
    distmat = indexvec2distmat_l2(np.array(embedded), faiss_res_in_df_ind, I_in_df_ind)

    min_inds = []
    min_value = 100000
    comb_iter = conf['combination_iter']
    target_num = conf['target_num']

    if len(faiss_res_in_df_ind)<= conf['combination_iter_thrsold']:
        numbers = np.arange(len(faiss_res_in_df_ind))
        combinations = list(itertools.combinations(numbers, min(len(faiss_res_in_df_ind), target_num))) ## len(numbers) < target_num인 경우 오류나서 min()설정
        random.shuffle(combinations)
    else: 
        combinations = [np.random.choice(len(faiss_res_in_df_ind), min(len(faiss_res_in_df_ind), target_num), replace=False) for _ in range(comb_iter)]
        
    for i in range(min(comb_iter, len(combinations))):
        random_integers = [x for x in combinations[i]]
        sim_mat = distmat[random_integers]
        if costfunc_min(sim_mat, I_in_df_ind, num_of_choice_each, conf['menu_weight_per_person']) < min_value:
            min_inds = random_integers
            min_value = costfunc_min(sim_mat, I_in_df_ind, num_of_choice_each, conf['menu_weight_per_person'])
    output_inds = np.array(faiss_res_in_df_ind)[min_inds]

############ distmat정의부터 여기까지 6초 걸림

    price_sample = []
    for i in range(len(df)):
        price_sample.append(([x[1] for x in df[i]['menu_squeeze']]))
    median_sample = []
    # low25_sample = []
    # high25_sample = []
    error = []
    median_index=[]
    for ind, x in enumerate(price_sample):
        try:
            p = [i for i in x if type(i)!=str]
            medp = np.median(p)
            if not np.isnan(medp):
                median_sample.append(medp)
                median_index.append(ind)
    #         low25_sample.append(np.quantile(p,q=0.25))
    #         high25_sample.append(np.quantile(p,q=0.75))
        except: ## 가격이 empty거나 '변동'이라고만 되어있는 경우
            error.append(x)

    iterator = iter(user_input_ind)
    split_lists = []
    for size in num_of_choice_each:
        split_lists.append(list(islice(iterator, size)))

    example = [[price_sample[x] for x in each] for each in split_lists] 
    med_interval = []
    for i in range(len(example)):
        med_tmp = []
        for j in example[i]:
            j_tmp = [x for x in j if x!='변동']
            if len(j_tmp)>0:
                med_tmp.append(int(np.median(j_tmp)))
        sort_med = sorted(med_tmp)
        if len(sort_med)!=0:
            med_interval.append((sort_med[0], sort_med[-1]))
        else:
            pass
    
    print('med_interval', med_interval)
    if len(med_interval)>1:  # 사람이 2명 이상인 경우
        exact_overlap_intervals = calculate_exact_overlap_intervals(med_interval)
        overlap_interval_sorted_False = np.sort([x for x in exact_overlap_intervals.keys()])[::-1]
        print('overlap_interval_sorted_False', overlap_interval_sorted_False)
        price_median_range = exact_overlap_intervals[overlap_interval_sorted_False[0]]
        print('price_median_range', price_median_range)
        satisfied_price_cond = overlap_median_price(price_median_range, output_inds, ratio_dict, df)
        user_input_dupl_index = [x[0] for x in Counter(user_input_ind).most_common() if x[1]>= max(len(split_lists)-1, 2)]
        satisfied_price_cond += [[x,ratio_dict[df[x]['obj_key']]] for x in user_input_dupl_index]
        satisfied_price_cond = np.unique(satisfied_price_cond, axis=0)
        i = 1
        while len(satisfied_price_cond) < conf["num_of_final_results"] :
            if i>=len(exact_overlap_intervals):
                break
            print('satisfied_price_cond', len(satisfied_price_cond))
            print('exact_overlap_intervals', exact_overlap_intervals)
            print('index', overlap_interval_sorted_False[i])
            price_median_range = exact_overlap_intervals[overlap_interval_sorted_False[i]]
            print('price_median_range', price_median_range)
            satisfied_price_cond = overlap_median_price(price_median_range, output_inds, ratio_dict, df)
        ### 유저들이 처음 넣은 output에서 겹치는 게 있다면 넣기
            user_input_dupl_index = [x[0] for x in Counter(user_input_ind).most_common() if x[1]>= max(len(split_lists)-1, 2)]
            satisfied_price_cond += [[x,ratio_dict[df[x]['obj_key']]] for x in user_input_dupl_index]
            satisfied_price_cond = np.unique(satisfied_price_cond, axis=0)
            i+=1
    else:
        satisfied_price_cond = []
        for ind in range(len(output_inds)):
            satisfied_price_cond.append([output_inds[ind], ratio_dict[df[output_inds[ind]]['obj_key']]])
        user_input_dupl_index = [x[0] for x in Counter(user_input_ind).most_common() if x[1]>= max(len(split_lists)-1, 2)]
        satisfied_price_cond += [[x,ratio_dict[df[x]['obj_key']]] for x in user_input_dupl_index]
        satisfied_price_cond = np.unique(satisfied_price_cond, axis=0)


    ## 공통가격이 없는 등의 이유로 가격조건을 통과한 최종 후보가 num_of_final_results 수보다 작으면 유사도 통과한 애들을 모두 포함시키기
    # if len(satisfied_price_cond) < conf["num_of_final_results"]: 
    #     satisfied_price_cond2 = []
    #     for ind in range(len(output_inds)):
    #         satisfied_price_cond2.append([output_inds[ind], ratio_dict[df[output_inds[ind]]['obj_key']]])
    #     user_input_dupl_index = [x[0] for x in Counter(user_input_ind).most_common() if x[1]>= max(len(split_lists)-1, 2)]
    #     satisfied_price_cond2 += [[x,ratio_dict[df[x]['obj_key']]] for x in user_input_dupl_index]
    #     satisfied_price_cond2 = np.unique(satisfied_price_cond2, axis=0)
    #     final_suggest_score = sorted(satisfied_price_cond2, key=(lambda x: x[1]), reverse=True)
    # else:
    #     final_suggest_score = sorted(satisfied_price_cond, key=(lambda x: x[1]), reverse=True)
    final_suggest_score = sorted(satisfied_price_cond, key=(lambda x: x[1]), reverse=True)
    final_suggest_obj_key = [df[int(x[0])]['obj_key']  for x in final_suggest_score]
    
    print('최초 유저 input:', [df[x]['title'] for x in user_input_ind])
    print('유저끼리 겹친 input:' ,user_input_dupl_index)
    print('loc조건 통과 수 :', len(satisfied_loc_cond))
    print('긍부정threshold 통과해서 유사도db에 넣는 식당 수 :', len(satisfied_db_indexing))
    print('유사도 통과한 식당 수 ', len(output_inds))
    print('가격조건까지 통과한 수 :', len(satisfied_price_cond))
    
    print(final_suggest_obj_key)
    try:
        doc_ref.update({'candidates': firestore.ArrayUnion(final_suggest_obj_key[:conf["num_of_final_results"]])})
    except:
        doc_ref.update({'candidates': firestore.ArrayUnion(final_suggest_obj_key)})
    return '0'
    # return final_suggest_ind

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9800)