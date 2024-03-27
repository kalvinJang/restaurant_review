import itertools
from itertools import islice
import numpy  as np
import copy

def find_combinations(lst, num):
    # 리스트에서 3개 요소의 모든 조합을 찾음
    return list(itertools.combinations(lst, num))

def get_circumcenter(points, eps):
    # return : tuple (원 중심, 원 반지름)
    x1, y1 = points[0]
    x2, y2 = points[1]
    x3, y3 = points[2]
    x = (x1**2*y2 - x1**2*y3 - x2**2*y1 + x2**2*y3 + x3**2*y1 - x3**2*y2 + y1**2*y2 - y1**2*y3 - y2**2*y1 + y2**2*y3 + y3**2*y1 - y3**2*y2)
    x /=  2*x1*y2 - 2*x1*y3 - (2*x2*y1 - 2*x2*y3) + 2*x3*y1 - 2*x3*y2

    y = -(x1**2*x2 - x1**2*x3 - x2**2*x1 + x2**2*x3 + x3**2*x1 - x3**2*x2 + y1**2*x2 - y1**2*x3 - y2**2*x1 + y2**2*x3 + y3**2*x1 - y3**2*x2)
    y /=  2*x1*y2 - 2*x1*y3 - (2*x2*y1 - 2*x2*y3) + 2*x3*y1 - 2*x3*y2
    return np.array([x, y]), np.sqrt((x1-x)**2 + (y1-y)**2) + eps

def get_center_radius(points): 
    # return : tuple (원 중심, 원 반지름)
    p1, p2, p3 = np.array(points[0]), np.array(points[1]), np.array(points[2])
    d1, d2, d3 = np.linalg.norm(p1 - p2), np.linalg.norm(p2 - p3), np.linalg.norm(p3 - p1)
    eps = (d1 + d2 + d3)/3 * 5e-2
    sorted = np.sort([d1, d2, d3])
    if sorted[0] **2 + sorted[1]**2 < sorted[2]**2:
        return (p2 + p3)/2, sorted[2]/2 + eps
    else:
        return get_circumcenter(points, eps)

def circle_score(points, target_p, radius):
    dist_vector = np.linalg.norm(points - target_p, axis=1)
    insiders = (dist_vector < radius).sum()
    return [insiders / radius**2, insiders]

def pick_circle_index(score_list, num, min_contain_thold):
    candidates = [x[0] if x[1] >= num * min_contain_thold else 0 for x in score_list]
    return np.argmax(candidates)

def get_outsiders(points, target_p, radius):
    dist_vector = np.linalg.norm(points - target_p, axis=1)
    return [x for i, x in enumerate(points) if dist_vector[i] > radius]

def get_circles(data, min_contain_thold, min_score_decay_thold, min_elem_decay_thold):
    # min_contain_thold : 처음 원 찾을 때 전체 포인트의 몇 퍼센트를 포함시킬 것이냐 + outsider중 다음 원에 포함될 최소 퍼센트 비율
    # min_score_decay_thold : 다음 원 찾을 때 점수를 얼마나 decay 허용할 것인지 비율
    # min_elem_decay_thold : 다음 원 찾을 때 포함되는 포인트 수를 얼마나 decay 허용할 것인지 비율 (이전 원의 몇 퍼센트만 있어도 되나)
    pred_score = 0
    pred_inners = 0
    treasures = []
    left_data = copy.deepcopy(data)

    if len(left_data)<3:
        for coor in left_data:
            treasures.append((np.array(coor), 0.003))
    elif len(left_data)>=3:
        while len(left_data) >= 3:
            scores = []
            combs = find_combinations(left_data, 3)
            for x in combs:
                x1, x2, x3 = x
                if x1==x2 or x2==x3 or x3==x1:
                    continue
                try:
                    scores.append(circle_score(left_data, *get_center_radius(x)))
                except:
                    print(x)
                    raise ZeroDivisionError
            if len(scores)==0:
                for coor in left_data:
                    treasures.append((np.array(coor), 0.003))
                break
            pick_thold = min_contain_thold if pred_score == 0 else pred_inners * min_elem_decay_thold/len(left_data)
            picked_index = pick_circle_index(scores, len(left_data), pick_thold)
            if scores[picked_index][0] > pred_score * min_score_decay_thold and scores[picked_index][1] > pred_inners * min_elem_decay_thold:
                pred_score, pred_inners = scores[picked_index][0], scores[picked_index][1]
                treasures.append(get_center_radius(combs[picked_index]))
                left_data = get_outsiders(left_data, *get_center_radius(combs[picked_index]))
            else:
                break
    return treasures

def indexing(item, embedded_ind):
    ### item :  원래 df3 인덱스 
    ### return: 멀티프로세스로 돌린 임베딩 결과의 인덱스 
    return embedded_ind[item]

def indexvec2distmat_l2(data, index_vector, target_vector):
    candidate_mat = data[index_vector]
    target_mat = data[target_vector]
    return np.sqrt(((candidate_mat[:, np.newaxis] - target_mat)**2).sum(axis=2))

def costfunc_min(mat, to_df_ind, num_of_choice_each, max_weight):
    iterator = iter(to_df_ind)
    split_lists = []
    for size in num_of_choice_each:
        split_lists.append(list(islice(iterator, size)))
    x0 = 0
    sub_min_ind = []
    for x in num_of_choice_each:
        kth_min = min(max_weight, x)
        sub_min_ind += np.argpartition(mat.min(0)[x0:x0+x], kth_min-1)[:kth_min].tolist()
        x0=x
    return mat[:, sub_min_ind].min(0).sum()

def calculate_exact_overlap_intervals(intervals):
    # Create a list of all start and end points, marking them as such
    events = []
    for start, end in intervals:
        events.append((start, 'start'))
        events.append((end, 'end'))
    print('calculate_exact_overlap_intervals function events', events)

    # Sort the events so we process them in order
    events.sort()

    # Dictionary to store the final result and current overlap counter
    overlap_dict = {}
    current_overlap = 0
    last_point = None
 
    # Iterate over each event
    for point, kind in events:
        if last_point is None:
            last_point = point
            continue
        
        if last_point is not None and current_overlap not in overlap_dict:
            overlap_dict[current_overlap] = []
        if last_point is not None and point != last_point:
            overlap_dict[current_overlap].append((last_point, point))

        # Update overlap counter
        if kind == 'start':
            current_overlap += 1
        else:
            current_overlap -= 1

        last_point = point

    temp_overlap_dict = copy.deepcopy(overlap_dict)
    for keys in temp_overlap_dict:
        if len(temp_overlap_dict[keys])==0:
            del overlap_dict[keys]
    return overlap_dict

def overlap_median_price(price_median_range, output_inds, ratio_dict, df):
    output_median_price = [np.median([x[1] for x in df[i]['menu_squeeze'] if x[1]!='변동']) for i in output_inds]
    satisfied_price_cond  = []
    for interval in price_median_range:
        min_median = interval[0]
        max_median = interval[1]
        for ind, med_ind in enumerate(output_median_price):
            if (min_median < med_ind) & (max_median > med_ind):
                satisfied_price_cond.append([output_inds[ind], ratio_dict[df[output_inds[ind]]['obj_key']]])
    return satisfied_price_cond