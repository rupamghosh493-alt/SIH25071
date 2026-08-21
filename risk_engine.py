def assess_risk(fs, reinforcement, displacement, rainfall, slope_angle):
    score=0
    reasons=[]
    if fs < 1.2: score += 45; reasons.append('Very low Factor of Safety')
    elif fs < 1.4: score += 35; reasons.append('Factor of Safety below 1.4')
    elif fs < 1.6: score += 15; reasons.append('Factor of Safety is getting close to the warning range')
    if reinforcement < .3: score += 30; reasons.append('Low reinforcement')
    elif reinforcement < .4: score += 20; reasons.append('Reinforcement below 0.4')
    elif reinforcement < .55: score += 8
    if displacement > 12: score += 20; reasons.append('High displacement')
    elif displacement > 8: score += 12; reasons.append('Elevated displacement')
    elif displacement > 5: score += 5
    if rainfall > 15: score += 10; reasons.append('Heavy rainfall')
    elif rainfall > 8: score += 5
    if slope_angle > 70: score += 10; reasons.append('Very steep slope')
    elif slope_angle > 62: score += 5
    score=min(100,round(score))
    level='Critical' if score>=80 else 'High' if score>=60 else 'Moderate' if score>=35 else 'Low'
    return score,level,reasons
