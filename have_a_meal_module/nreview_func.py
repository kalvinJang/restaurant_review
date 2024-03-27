from flask import Flask, request, jsonify
from pyngrok import conf, ngrok
from flask_cors import CORS
import pickle
import datetime 
import numpy as np
import pandas as pd

def find_nreview(long_bads, keyword):   ## 엔리뷰 홈페이지 -  부정 리뷰만 보여주는 화면
    with open('../../../david/search/'+datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '['+ keyword +']' +'.pkl', 'wb') as f:
        pickle.dump(keyword, f) 
    keyword = keyword.replace('admin', '')
    tmp = long_bads[long_bads['squeezed_title']==keyword.replace(' ', '')].copy()
    if tmp.shape[0] == 0:
        tmp = long_bads[[True if keyword.replace(' ', '') in x else False for x in long_bads['squeezed_title']]].copy()
    tmp.reset_index(drop=True, inplace=True)
    tmp['식당'] = tmp['title']
    tmp['위치'] = tmp['loc']
    tmp['방문일'] = tmp['date_kor'].apply(lambda x: x.strftime('%Y-%m-%d'))
    # tmp['해당 유저의 방문횟수'] = tmp['visit_num']
    tmp['리뷰'] = tmp['no_tag_review']
    tmp['해당 유저의 (부정리뷰) /(전체리뷰)'] = tmp['user_stat']
    tmp = tmp[~tmp['리뷰'].str.contains('네이버 예약')]
    tmp['번호'] = tmp.reset_index(drop=True).index.tolist()
    return tmp[['번호', '식당', '주차', '위치', '방문일', '리뷰', '해당 유저의 (부정리뷰) /(전체리뷰)']].to_json(orient='records', force_ascii=False)

def find_nreview2(long_bads, df, keyword):
    check_num = 0
    with open('../../../david/kakao/'+datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '['+ keyword +']' +'.pkl', 'wb') as f:
        pickle.dump(keyword, f) 
    keyword = keyword.replace('admin', '')
    if '#' in keyword:
        check = keyword.split('#')
        keyword = check[0]
        check_num = int(check[-1])
    tmp = long_bads[long_bads['squeezed_title']==keyword.replace(' ', '')].copy()  ## tmp : 해당 식당의 나쁜 리뷰만 모아져있음
    tmp_total = df[df['squeezed_title']==keyword.replace(' ', '')].copy()    ## tmp_total : 해당 식당의 모든 리뷰가 모아져있음
    if (tmp.shape[0] == 0) and (tmp_total.shape[0] == 0): # 나쁜리뷰도 없고 좋은 리뷰도 없음
        try:
            tmp2 = long_bads[[True if keyword.replace(' ', '') in x else False for x in long_bads['squeezed_title']]].copy()
            if tmp2.shape[0]==0:
                text = '해당 식당의 안 좋은 리뷰를 찾지 못했습니다ㅠㅠ \n 검색어가 네이버에 등록된 식당인지 다시 확인해주세요'
            else:
                candidate = ' / '.join(np.unique(tmp2['title'].values))
                text = '해당 식당의 안 좋은 리뷰를 찾지 못했습니다ㅠㅠ \n\n 혹시 [ {} ] 이 중에 찾으시는 식당이 있나요?'.format(candidate)
        except:
            text = '해당 식당의 안 좋은 리뷰를 찾지 못했습니다ㅠㅠ \n 검색어가 네이버에 등록된 식당인지 다시 확인해주세요'
    elif (tmp.shape[0] == 0):  # 나쁜 리뷰만 없음
        try:
            tmp_good = tmp_total[tmp_total['pred_label']=='LABEL_1']
            tmp_good.reset_index(drop=True, inplace=True)
            tmp_good['식당'] = tmp_good['title']
            tmp_good['위치'] = tmp_good['loc']
            tmp_good['방문일'] = tmp_good['date_kor'].apply(lambda x: x.strftime('%Y-%m-%d'))
            # tmp['해당 유저의 방문횟수'] = tmp['visit_num']
            tmp_good['리뷰'] = tmp_good['no_tag_review']
            tmp_good = tmp_good[~tmp_good['리뷰'].str.contains('네이버 예약')]
            tmp_good['번호'] = tmp_good.reset_index(drop=True).index.tolist()
            locations = tmp_good['위치'].unique().tolist()
            wanted_loc = locations[check_num-1]
            tmp_good = tmp_good[tmp_good['위치']==wanted_loc]
            tmp_good[tmp_good['no_tag_review'].apply(lambda x: len(x)>20)]
            text = '[' +tmp_good['식당'].iloc[0] +' - '+ tmp_good['위치'].iloc[0] + ']\n 긍정리뷰 비율 : 100%...!!\n\n'
            text += '------[긍정리뷰 top 5]------\n-----------------------------------\n'
            for i in range(min(5, tmp_good.shape[0])):
                text += '- ' + tmp_good['리뷰'].iloc[i] + ' (' + tmp_good['방문일'].iloc[i] + ')' + '\n\n'
        except:
            text = '해당 식당의 안 좋은 리뷰를 찾지 못했습니다ㅠㅠ \n 검색어가 네이버에 등록된 식당인지 다시 확인해주세요'
    else:  # 나쁜 리뷰 존재
        try:
            tmp.reset_index(drop=True, inplace=True)
            tmp['식당'] = tmp['title']
            tmp['위치'] = tmp['loc']
            tmp['방문일'] = tmp['date_kor'].apply(lambda x: x.strftime('%Y-%m-%d'))
            # tmp['해당 유저의 방문횟수'] = tmp['visit_num']
            tmp['리뷰'] = tmp['no_tag_review']
            tmp['해당 유저의 (부정리뷰) /(전체리뷰)'] = tmp['user_stat']
            tmp = tmp[~tmp['리뷰'].str.contains('네이버 예약')]
            tmp['번호'] = tmp.reset_index(drop=True).index.tolist()
            locations = tmp['위치'].unique().tolist()
            wanted_loc = locations[check_num-1]
            print(1)
            tmp_good = tmp_total[tmp_total['pred_label']=='LABEL_1']
            tmp_good.reset_index(drop=True, inplace=True)
            tmp_good['식당'] = tmp_good['title']
            tmp_good['위치'] = tmp_good['loc']
            tmp_good['방문일'] = tmp_good['date_kor'].apply(lambda x: x.strftime('%Y-%m-%d'))
            # tmp['해당 유저의 방문횟수'] = tmp['visit_num']
            tmp_good['리뷰'] = tmp_good['no_tag_review']
            tmp_good = tmp_good[~tmp_good['리뷰'].str.contains('네이버 예약')]
            tmp_good['번호'] = tmp_good.reset_index(drop=True).index.tolist()

            tmp = tmp[tmp['위치']==wanted_loc]
            tmp_good = tmp_good[tmp_good['위치']==wanted_loc]
            tmp_good[tmp_good['no_tag_review'].apply(lambda x: len(x)>20)]
            # tmp_good = tmp_good[]
            text = '[' +tmp['식당'].iloc[0] +' - '+ tmp['위치'].iloc[0] + ']\n 긍정리뷰 비율 : ' + str(round((1 - tmp[tmp['updated_pred_label']==0].shape[0] / tmp_total['total_review_counts'].iloc[0]) * 100, 2)) + '%\n\n'
            text += '------[긍정리뷰 top 5]------\n-----------------------------------\n'
            for i in range(min(5, tmp_good.shape[0])):
                text += '- ' + tmp_good['리뷰'].iloc[i] + ' (' + tmp_good['방문일'].iloc[i] + ')' + '\n\n'
            text += '----------------[부정리뷰]----------------\n----------------------------------------------\n'
            for i in range(tmp.shape[0]):
                text += '- ' + tmp['리뷰'].iloc[i] + ' (' + tmp['방문일'].iloc[i] + ')' + '\n\n'
            
        except:
            text = '해당 식당의 안 좋은 리뷰를 찾지 못했습니다ㅠㅠ \n 검색어가 네이버에 등록된 식당인지 다시 확인해주세요' 

    # 답변 텍스트 설정
    res = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": text
                    }
                }
            ]
        }
    }
 
    # 답변 전송
    return jsonify(res)