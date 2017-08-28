# -*- coding: utf-8 -*-
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

from airflow.hooks.athena_hook import AthenaHook
from airflow.hooks.mysql_hook import MySqlHook
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults


class AthenaToMySqlTransfer(BaseOperator):
    """
    Moves data from Athena to MySQL, note that for now the data is loaded
    into memory before being pushed to MySQL, so this operator should
    be used for smallish amount of data.

    :param sql: SQL query to execute against the MySQL database
    :type sql: str
    :param mysql_table: target MySQL table, use dot notation to target a
        specific database
    :type mysql_table: str
    :param mysql_conn_id: source mysql connection
    :type mysql_conn_id: str
    :param athena_conn_id: source athena connection
    :type athena_conn_id: str
    :param mysql_preoperator: sql statement to run against mysql prior to
        import, typically use to truncate of delete in place of the data
        coming in, allowing the task to be idempotent (running the task
        twice won't double load data)
    :type mysql_preoperator: str
    """

    template_fields = ('sql', 'mysql_table', 'mysql_preoperator')
    template_ext = ('.sql',)
    ui_color = '#a0e08c'

    @apply_defaults
    def __init__(
            self,
            sql,
            mysql_table,
            athena_conn_id='athena_default',
            mysql_conn_id='mysql_default',
            mysql_preoperator=None,
            *args, **kwargs):
        super(AthenaToMySqlTransfer, self).__init__(*args, **kwargs)
        self.sql = sql
        self.mysql_table = mysql_table
        self.mysql_conn_id = mysql_conn_id
        self.mysql_preoperator = mysql_preoperator
        self.athena_conn_id = athena_conn_id

    def execute(self, context):
        athena = AthenaHook(athena_conn_id=self.athena_conn_id)
        logging.info("Extracting data from Athena")
        logging.info(self.sql)
        results = athena.get_records(self.sql)

        mysql = MySqlHook(mysql_conn_id=self.mysql_conn_id)
        if self.mysql_preoperator:
            logging.info("Running MySQL preoperator")
            logging.info(self.mysql_preoperator)
            mysql.run(self.mysql_preoperator)

        logging.info("Inserting rows into MySQL")
        mysql.insert_rows(table=self.mysql_table, rows=results)
