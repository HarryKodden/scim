import os
import json

from typing import Any
from data.plugins import Plugin

import sqlalchemy as db
from sqlalchemy.orm import sessionmaker

class SQLPlugin(Plugin):

    def __init__(self, resource_type: str, address: str = 'sqlite:///test.sqlite'):

      self.resource_type = resource_type
      self.description = f"SQL-{resource_type}"

      engine = db.create_engine(address)
      self.Session = sessionmaker(engine)

      self.connection = engine.connect()

      metadata = db.MetaData()

      self.table = db.Table(
        self.resource_type,
        metadata,
        db.Column('id', db.String(255)),
        db.Column('details', db.Text, nullable=False)
      )

      metadata.create_all(engine)

    def __iter__(self) -> Any:
      rows = self.connection.execute(
        db.select(self.table) 
      ).fetchall()
      
      for row in rows:
        yield row['id']
  
    def __delete__(self, id: str) -> None:
      with self.Session() as session:
          self.db.cursor().execute(
            f"DELETE FROM {self.resource_type} WHERE id = '{id}'"
          )
          session.commit()

    def __getitem__(self, id: str) -> Any:
      try:
        rows = self.connection.execute(
          db.select([self.table.columns.details]).where(id == id)
        ).fetchall()

        if len(rows) != 1:
          raise Exception(f"No match for id: {id}")

        return(rows[0]) | { 'id': id }
      except Exception:
        return None

    def __setitem__(self, id: str, details: Any) -> None:

      with self.Session() as session:
        if self[id]:
          self.connection.execute(
            self.db.update(
              self.table
            ).values(
              details = json.dumps(details)
            ).where(
              id==id
            )
          )
        else: 
          self.connection.execute(
            self.db.insert(
              self.table
            ).values(
              id=id,
              details=json.dumps(details)
            )
          )

          session.commit()
