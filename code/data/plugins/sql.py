import json

from typing import Any, Callable
from data.plugins import Plugin

import sqlalchemy as db
from sqlalchemy.orm import Session

from contextlib import contextmanager, AbstractContextManager

from sqlalchemy.dialects.postgresql import JSON

import logging
logger = logging.getLogger(__name__)


class SQLPlugin(Plugin):

    def __init__(
        self,
        resource_type: str,
        database_url: str = "sqlite:///scim.sqlite"
    ):

        self.resource_type = resource_type
        self.description = f"SQL-{resource_type}"

        engine = db.create_engine(database_url)

        self._session_factory = db.orm.scoped_session(
            db.orm.sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=engine,
            ),
        )

        with self.Transaction():

            metadata = db.MetaData()

            self.table = db.Table(
                self.resource_type,
                metadata,
                db.Column('id', db.String(255), primary_key=True),
                db.Column('details', JSON, nullable=False)
            )

            metadata.create_all(engine)

    @contextmanager
    def Transaction(self) -> Callable[..., AbstractContextManager[Session]]:

        session: Session = self._session_factory()
        try:
            yield session
        except Exception:
            logger.exception("Session rollback because of exception")
            session.rollback()
            raise
        finally:
            session.flush()
            session.commit()
            session.close()

    def __iter__(self) -> Any:
        logger.debug(f"[__iter__]: {self.description}")

        with self.Transaction() as session:
            rows = session.execute(
              db.select(self.table.columns.id)
            ).fetchall()

            logger.debug(f"Nr rows found: {len(rows)}")

            for row in rows:
                yield row[0]

    def __delitem__(self, id: str) -> None:
        logger.debug(f"[__delitem__]: {self.description}, id:{id}")

        with self.Transaction() as session:
            stmt = db.delete(
                self.table
            ).where(
                self.table.columns.id == id
            )

            logger.debug(f"[SQL]: {stmt}")

            session.execute(stmt)

    def __getitem__(self, id: str) -> Any:
        logger.debug(f"[__getitem__]: {self.description}, id:{id}")

        try:
            with self.Transaction() as session:

                rows = session.execute(
                    db.select(
                        self.table.columns.details
                    ).where(
                        self.table.columns.id == id
                    )
                ).fetchall()

                if len(rows) != 1:
                    raise Exception(f"No match for id: {id}")

                return rows[0][0] | {'id': id}

        except Exception as e:
            logger.debug(f"[__getitem__]: error {str(e)}")
            return None

    def __setitem__(self, id: str, details: Any) -> None:
        logger.debug(
            f"[__setitem__]: {self.description}, id:{id}, details: {details}"
        )

        with self.Transaction() as session:

            if self[id]:
                stmt = db.update(
                    self.table
                ).values(
                    details=json.loads(details)
                ).where(
                    self.table.columns.id == id
                )
            else:
                stmt = db.insert(
                    self.table
                ).values(
                    id=id,
                    details=json.loads(details)
                )

            logger.debug(f"[SQL]: {stmt}")

            session.execute(stmt)
