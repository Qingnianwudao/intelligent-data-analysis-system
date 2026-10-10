import json
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.deps import get_current_subject
from app.models import AppMessage, AppSession
from app.schemas import (
    ChatResponse,
    ChartData,
    MessageCreate,
    MessageOut,
    SessionCreate,
    SessionOut,
    SessionUpdate,
)
from app.services.nl2sql_service import run_nl2sql_turn, stream_nl2sql_sse

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _parse_meta(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _message_out(m: AppMessage) -> MessageOut:
    return MessageOut(
        id=m.id,
        role=m.role,
        content=m.content,
        meta=_parse_meta(m.meta_json),
    )


def _load_history_pairs(db: Session, session_id: str) -> list[tuple[str, str]]:
    rows = db.scalars(
        select(AppMessage)
        .where(AppMessage.session_id == session_id)
        .order_by(AppMessage.id)
    ).all()
    return [(r.role, r.content) for r in rows]


@router.get("", response_model=list[SessionOut])
def list_sessions(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_current_subject)],
) -> list[AppSession]:
    return list(
        db.scalars(select(AppSession).order_by(AppSession.updated_at.desc())).all()
    )


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_current_subject)],
    body: SessionCreate | None = None,
) -> AppSession:
    sid = str(uuid.uuid4())
    title = (body.title.strip() if body and body.title else None) or "新会话"
    now = datetime.now(timezone.utc)
    row = AppSession(id=sid, title=title, created_at=now, updated_at=now)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{session_id}", response_model=SessionOut)
def update_session(
    session_id: str,
    body: SessionUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_current_subject)],
) -> AppSession:
    row = db.get(AppSession, session_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="会话不存在")
    row.title = body.title.strip() or row.title
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_current_subject)],
) -> None:
    row = db.get(AppSession, session_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="会话不存在")
    db.delete(row)
    db.commit()


@router.get("/{session_id}/messages", response_model=list[MessageOut])
def list_messages(
    session_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_current_subject)],
) -> list[MessageOut]:
    if not db.get(AppSession, session_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="会话不存在")
    rows = db.scalars(
        select(AppMessage)
        .where(AppMessage.session_id == session_id)
        .order_by(AppMessage.id)
    ).all()
    return [_message_out(m) for m in rows]


@router.post("/{session_id}/messages", response_model=ChatResponse)
def post_message(
    session_id: str,
    body: MessageCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_current_subject)],
) -> ChatResponse:
    sess = db.get(AppSession, session_id)
    if not sess:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="会话不存在")

    history = _load_history_pairs(db, session_id)
    try:
        pack = run_nl2sql_turn(history, body.content.strip())
    except RuntimeError as e:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"模型或 Agent 执行失败: {e!s}",
        ) from e

    um = AppMessage(session_id=session_id, role="user", content=body.content.strip())
    meta = {
        "sql": pack.get("sql"),
        "data": pack.get("data"),
        "meta": pack.get("meta"),
    }
    am = AppMessage(
        session_id=session_id,
        role="assistant",
        content=pack.get("reply") or "",
        meta_json=json.dumps(meta, ensure_ascii=False),
    )
    db.add(um)
    db.add(am)
    sess.updated_at = datetime.now(timezone.utc)
    db.commit()

    return ChatResponse(
        reply=pack.get("reply") or "",
        sql=pack.get("sql"),
        data=ChartData(**(pack.get("data") or {"columns": [], "rows": []})),
        meta=pack.get("meta") or {},
    )


@router.post("/{session_id}/messages/stream")
def post_message_stream(
    session_id: str,
    body: MessageCreate,
    _: Annotated[str, Depends(get_current_subject)],
) -> StreamingResponse:
    """SSE：event: step / event: final（final 的 JSON 与 POST …/messages 响应形状一致）。写入 DB 在流结束后完成。"""

    def event_gen():
        db = SessionLocal()
        try:
            sess = db.get(AppSession, session_id)
            if not sess:
                yield "event: error\ndata: {\"detail\":\"会话不存在\"}\n\n"
                return
            history = _load_history_pairs(db, session_id)
            final_pack: dict[str, Any] | None = None
            for block in stream_nl2sql_sse(history, body.content.strip()):
                yield block
                if block.startswith("event: final"):
                    line = block.split("data: ", 1)[1].strip() if "data: " in block else ""
                    if line:
                        try:
                            final_pack = json.loads(line)
                        except json.JSONDecodeError:
                            final_pack = None
            if final_pack is None:
                yield "event: error\ndata: {\"detail\":\"未收到 final 事件\"}\n\n"
                return
            um = AppMessage(
                session_id=session_id,
                role="user",
                content=body.content.strip(),
            )
            meta = {
                "sql": final_pack.get("sql"),
                "data": final_pack.get("data"),
                "meta": final_pack.get("meta"),
            }
            am = AppMessage(
                session_id=session_id,
                role="assistant",
                content=final_pack.get("reply") or "",
                meta_json=json.dumps(meta, ensure_ascii=False),
            )
            db.add(um)
            db.add(am)
            sess.updated_at = datetime.now(timezone.utc)
            db.commit()
        except RuntimeError as e:
            yield f"event: error\ndata: {json.dumps({'detail': str(e)}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'detail': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            db.close()

    return StreamingResponse(event_gen(), media_type="text/event-stream")
