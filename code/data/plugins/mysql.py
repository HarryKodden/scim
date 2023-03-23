import os
import json

from typing import Any
from data.plugins import Plugin

class MySQLPlugin(Plugin):

    def __init__(self, host, user, password, database):
      from mysql.connector import connect

      self.db = connect(
        host=host,
        user=user,
        password=password,
        database=database
      )

      try:
        self.db.cursor().execute("CREATE TABLE Users (id VARCHAR(50) NOT NULL, details JSON, PRIMARY KEY (id))")
      except:
        pass

      try:
        self.db.cursor().execute("CREATE TABLE Groups (id VARCHAR(50) NOT NULL, details JSON, PRIMARY KEY (id))")
      except:
        pass

      self.db.commit()
      
      self.description = 'MYSQL'

    def iterate(self, resource_type: str) -> Any:
      cursor = self.db.cursor(dictionary=True)
      cursor.execute(f"SELECT id FROM {resource_type}")
      rows = cursor.fetchall()
  
      for row in rows:
        yield row['id']
  
    def delete(self, resource_type: str, id: int) -> None:
      self.db.cursor().execute(
        f"DELETE FROM {resource_type} WHERE id = '{id}'"
      )

      self.db.commit()

    def read(self, resource_type: str, id: int) -> Any:
      try:
        self.mydb.cursor(
          dictionary=True
        ).execute(
          f"SELECT details FROM {resource_type} WHERE id = '{id}'"
        ).fetchall()[0] | { 'id': id }
      except Exception:
        return None

    def write(self, resource_type: str, id: int, details: Any) -> None:
      if self.read(resource_type, id):
        self.db.cursor().execute(
          f"UPDATE {resource_type} SET details = '{json.dumps(details)}' WHERE id = '{id}'"
        )
      else: 
        self.db.cursor().execute(
          f"INSERT INTO {resource_type} (id, details) VALUES (%s, %s)",
          (
            id,
            json.dumps(details)
          )
        )

      self.db.commit()
