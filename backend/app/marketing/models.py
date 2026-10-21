from datetime import datetime
from sqlalchemy import Column,Integer,String,DateTime,ForeignKey,UniqueConstraint
from app.database import Base

class SmsCampaignConfig(Base):
    __tablename__='marketing_sms_campaign_config'
    campaign_id=Column(Integer,ForeignKey('marketing_campaigns.id'),primary_key=True)
    purpose=Column(String(30),nullable=False)

class SmsDelivery(Base):
    __tablename__='marketing_sms_deliveries'
    __table_args__=(UniqueConstraint('campaign_id','phone',name='uq_marketing_sms_phone'),)
    id=Column(Integer,primary_key=True)
    campaign_id=Column(Integer,ForeignKey('marketing_campaigns.id'),nullable=False,index=True)
    contact_id=Column(Integer,ForeignKey('marketing_contacts.id'),nullable=False)
    phone=Column(String(30),nullable=False)
    status=Column(String(30),nullable=False,default='pending')
    provider_id=Column(String(80),nullable=True,index=True)
    error_code=Column(String(40),nullable=True)
    created_at=Column(DateTime,default=datetime.utcnow,nullable=False)
