import json
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.models import MarketplaceCustomer, SnsMessageLog, Tenant, TenantStatus

router = APIRouter(prefix="/v1/aws", tags=["AWS Marketplace"])


@router.post("/sns-webhook")
async def handle_sns_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    """
    AWS SNS webhook endpoint for marketplace subscription lifecycle events.
    """
    body_bytes = await request.body()
    try:
        payload = json.loads(body_bytes)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    msg_type = payload.get("Type")
    msg_id = payload.get("MessageId")
    topic_arn = payload.get("TopicArn")

    if not msg_id or not topic_arn:
        raise HTTPException(status_code=400, detail="SNS message missing MessageId or TopicArn")

    already_processed = db.query(SnsMessageLog).filter_by(message_id=msg_id).first()
    if already_processed:
        return {"status": "ignored", "reason": "message_already_processed"}

    if msg_type == "SubscriptionConfirmation":
        subscribe_url = payload.get("SubscribeURL")
        if not subscribe_url:
            raise HTTPException(status_code=400, detail="SubscriptionConfirmation missing SubscribeURL")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(subscribe_url)
            response.raise_for_status()

        db.add(SnsMessageLog(message_id=msg_id, topic_arn=topic_arn, raw_payload=payload))
        db.commit()
        return {"status": "confirmed"}

    if msg_type == "Notification":
        inner_message_raw = payload.get("Message", "{}")
        try:
            message_data = json.loads(inner_message_raw)
        except json.JSONDecodeError:
            message_data = {}

        action = message_data.get("action")
        customer_identifier = message_data.get("customer-identifier")

        if customer_identifier:
            customer = db.query(MarketplaceCustomer).filter_by(aws_customer_identifier=customer_identifier).first()
            if customer:
                tenant = db.query(Tenant).filter_by(id=customer.tenant_id).first()

                if action == "unsubscribe-success":
                    customer.subscription_status = "unsubscribed"
                    customer.unsubscribed_at = datetime.now(timezone.utc)
                    if tenant:
                        tenant.status = TenantStatus.SUSPENDED
                elif action in {"entitlement-updated", "subscribe-success"}:
                    customer.subscription_status = "active"
                    customer.unsubscribed_at = None
                    if tenant:
                        tenant.status = TenantStatus.ACTIVE

        db.add(SnsMessageLog(message_id=msg_id, topic_arn=topic_arn, raw_payload=payload))
        db.commit()
        return {"status": "processed", "action": action or "unknown"}

    db.add(SnsMessageLog(message_id=msg_id, topic_arn=topic_arn, raw_payload=payload))
    db.commit()
    return {"status": "ignored", "reason": "unknown_message_type"}
