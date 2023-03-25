import os
import json

from typing import Any
from data.plugins import Plugin

class MySQLPlugin(Plugin):

    def __init__(self, resource_type: str, host, user, password, database):
      from mysql.connector import connect

      self.db = connect(
        host=host,
        user=user,
        password=password,
        database=database
      )

      try:
        self.db.cursor().execute(f"CREATE TABLE {resource_type} (id VARCHAR(50) NOT NULL, details JSON, PRIMARY KEY (id))")
      except:
        pass

      self.db.commit()

      self.resource_type = resource_type
      self.description = f"MYSQL-{resource_type}"

    def __iter__(self) -> Any:
      cursor = self.db.cursor(dictionary=True)
      cursor.execute(f"SELECT id FROM {self.resource_type}")
      rows = cursor.fetchall()
  
      for row in rows:
        yield row['id']
  
    def __delete__(self, id: str) -> None:
      self.db.cursor().execute(
        f"DELETE FROM {self.resource_type} WHERE id = '{id}'"
      )

      self.db.commit()

    def __getitem__(self, id: str) -> Any:
      try:
        self.mydb.cursor(
          dictionary=True
        ).execute(
          f"SELECT details FROM {self.resource_type} WHERE id = '{id}'"
        ).fetchall()[0] | { 'id': id }
      except Exception:
        return None

    def __setitem__(self, id: str, details: Any) -> None:
      if self[id]:
        self.db.cursor().execute(
          f"UPDATE {self.resource_type} SET details = '{json.dumps(details)}' WHERE id = '{id}'"
        )
      else: 
        self.db.cursor().execute(
          f"INSERT INTO {self.resource_type} (id, details) VALUES (%s, %s)",
          (
            id,
            json.dumps(details)
          )
        )

      self.db.commit()
