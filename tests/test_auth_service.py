from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ops_agent.api.models.config_models import Base, UserModel


def test_user_model_table_can_store_first_admin(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'auth.db'}")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        user = UserModel(
            id="user-1",
            username="admin",
            password_hash="hash",
            role="admin",
            is_active=True,
        )
        session.add(user)
        session.commit()

        saved = session.query(UserModel).filter_by(username="admin").one()

    assert saved.id == "user-1"
    assert saved.role == "admin"
    assert saved.is_active is True
