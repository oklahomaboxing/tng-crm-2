"""Structured AI generation with an explicitly labeled editable-template fallback."""
import json,os
from fastapi import HTTPException

def template(prompt):
    lower=prompt.lower()
    topics=[(('youth','children','kids'),'Youth boxing','Build confidence, discipline and boxing skills with TNG Boxing’s youth programs.'),
            (('nutrition','shake','tea'),'NexGen Nutrition','Support your training with NexGen Nutrition at TNG Boxing.'),
            (('fight','ticket','bout'),'TNG fight night','Support local fighters and experience TNG Boxing fight night.'),
            (('sponsor',),'Support TNG Boxing','Connect your business with the TNG Boxing community.'),
            (('opening',),'Welcome to TNG Boxing','Visit TNG Boxing at 8416 NW Expressway, Oklahoma City.'),
            (('adult','fitness','beginner'),'Boxing for every starting point','Train boxing skills, improve fitness and build confidence with TNG Boxing.')]
    title,copy='TNG Boxing member update','Stay connected with your TNG Boxing community.'
    for words,name,message in topics:
        if any(word in lower for word in words):title,copy=name,message;break
    return {'subject':title,'email':f'Hi {{{{first_name}}}},\n\n{copy}\n\nContact the gym for current schedules and details: 405-959-5823 or marketing@tngboxinggym.com.\n\nTNG Boxing\nEarned Not Given.',
            'sms':f'TNG Boxing: {copy} Call 405-959-5823 for details. Reply STOP to opt out.',
            'social':f'{copy}\n\nContact TNG Boxing for current details. Earned Not Given.',
            'generation_source':'template','notice':'AI generation is unavailable. An editable template is ready; add and verify your campaign details before sending.'}

def generate(prompt,client):
    prompt=prompt.strip()
    if not prompt or len(prompt)>4000:raise HTTPException(400,'Enter a campaign brief between 1 and 4,000 characters.')
    if not os.getenv('OPENAI_API_KEY'):return template(prompt)
    try:
        response=client.with_options(timeout=15,max_retries=0).chat.completions.create(
            model=os.getenv('MARKETING_AI_MODEL','gpt-4.1'),response_format={'type':'json_object'},temperature=0.7,
            messages=[{'role':'system','content':'Write TNG Boxing campaign drafts. Return a JSON object with string fields subject, email, sms, social. Use only facts in the brief. Do not invent prices, dates, promotions, availability or promises. Use {{first_name}} for optional personalization. Identify TNG Boxing in SMS. Never send anything.'},{'role':'user','content':prompt}])
        data=json.loads(response.choices[0].message.content)
        if not isinstance(data,dict) or not all(isinstance(data.get(k),str) and data[k].strip() for k in ['subject','email','sms','social']):raise ValueError()
        if any(len(data[k])>12000 for k in ['subject','email','sms','social']):raise ValueError()
        return {k:data[k] for k in ['subject','email','sms','social']}|{'generation_source':'ai','notice':'AI draft generated. Review the details before sending.'}
    except Exception:
        return template(prompt)
