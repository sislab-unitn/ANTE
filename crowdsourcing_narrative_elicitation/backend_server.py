import json
import os
import sqlite3
import random
import tomllib
import string
from datetime import datetime
from db_utils import DBUtils


class Server:
    def __init__(self, config_path: str) -> None:
        assert os.path.exists(config_path), f"config file not found at {config_path}"
        with open("config.toml", "rb") as f:
            config = tomllib.load(f)
        self.port = config["server"]["port"]
        self.host = config["server"]["host"]
        self.sign_in = config["pages"]["sign_in"]
        self.guidelines = config["pages"]["guidelines"]
        self.example = config["pages"]["example"]
        self.data_collection = config["pages"]["data_collection"]
        self.completion = config["pages"]["completion"]
        self.assets = config["assets"]["assets"]
        self.data = config["data"]["data"]
        self.db = config["data"]["db"]
        self.blacklist = config["data"]["blacklist"]
        self.batch_size = config["data"]["batch_size"]
        self.num_batches = config["data"]["num_batches"]
        self.completion_code = config["prolific"]["completion_code"]
        assert os.path.exists(self.sign_in), f"sign_in page not found at {self.sign_in}"
        assert os.path.exists(
            self.guidelines
        ), f"guidelines page not found at {self.guidelines}"
        assert os.path.exists(
            self.data_collection
        ), f"data_collection page not found at {self.data_collection}"
        assert os.path.exists(self.assets), f"assets not found at {self.assets}"
        assert os.path.exists(self.data), f"data not found at {self.data}"

        self.init_tables()
        with open(self.data, "rb") as f:
            narratives = json.load(f)
            print(f"there are a total of {len(narratives)}")
            with open(config["data"]["blacklist"], "rb") as f:
                blacklist = json.load(f)
                print(len(blacklist["black_listed_narrative_ids"]))
            narratives = self.remove_blacklist(narratives, blacklist)
            print(f"after removing blacklisted elements there are a total of {len(narratives)}")
        try:
            self.insert_narratives(narratives)
            # print (len(narratives))
            num_batches = self.num_batches
            batches = self.split_narratives(narratives, num_batches)
            assert self.verify_split(batches), "Narratives not split correctly"
            # batches = self.split_narratives(narratives, num_batches)
            batches_len = [len(batch) for batch in batches]
            print (f"The sizes of the batches created are {batches_len}")
            self.insert_batches(batches)
        except sqlite3.IntegrityError:
            print("narratives already inserted")

    def remove_blacklist(self, narratives: list, blacklist: list) -> list:
        cleaned_narratives = [
            narrative
            for narrative in narratives
            if narrative["id"] not in blacklist["black_listed_narrative_ids"]
        ]
        return cleaned_narratives

    def init_tables(
        self,
    ) -> None:
        conn = DBUtils.create_connection(db_file=self.db)

        DBUtils.create_table(
            table="Cookie_to_Prolific_ID",
            fields=[
                "Cookie PRIMARY KEY",
                "Prolific_ID",
                "First_accessed_timestamp",
                "First_narrative_timestamp",
            ],
            conn=conn,
        )
        DBUtils.create_table(
            "Batch_ID_to_Cookie",
            [
                "Batch_ID",
                "Cookie",
            ],
            conn,
        )
        DBUtils.create_table(
            "Example_ID_to_Cookie",
            ["Example_ID", "Example_answer", "Cookie", "Timestamp"],
            conn,
        )
        DBUtils.create_table(
            "Batch_ID_to_Narrative_ID", ["Batch_ID", "Narrative_ID"], conn
        )
        DBUtils.create_table(
            "Narrative_ID_to_Narrative_data",
            ["Narrative_ID PRIMARY KEY", "Narrative_data"],
            conn,
        )
        DBUtils.create_table(
            "Completed_narratives",
            [
                "Cookie",
                "Narrative_ID",
                "Completion_data",
                "Narrative_completion_timestamp",
            ],
            conn,
        )
        DBUtils.create_table(
            "Completion_codes",
            [
                "Cookie",
                "Batch_ID",
                "Completion_code PRIMARY KEY",
                "Completion_timestamp",
            ],
            conn,
        )
        DBUtils.create_table("Expired_Cookie", ["Cookie PRIMARY KEY"], conn)
        conn.close()

    def insert_narratives(self, narratives: list) -> None:
        conn = DBUtils.create_connection(db_file=self.db)
        for narrative in narratives:
            DBUtils.insert_row(
                table="Narrative_ID_to_Narrative_data",
                fields=["Narrative_ID", "Narrative_data"],
                values=[narrative["id"], json.dumps(narrative)],
                conn=conn,
            )
        conn.close()

    def verify_split(self, batches: list) -> bool:
        # check that all narratives in batch have different ids
        for batch in batches:
            counts = {}
            for narrative in batch:
                counts[narrative["id_narrative"].split("_")[0]] = 0
                ids = [nar["id_narrative"].split("_")[0] for nar in batch]
                for id in ids:
                    if narrative["id_narrative"].split("_")[0] == id:
                        counts[id] += 1
            for key in counts:
                if counts[key] > 1:
                    return False
        return True

    def split_narratives(self, narratives: list, n: int) -> list or None:
        # stratify by length
        split = [[] for _ in range(n)]
        narratives = sorted(narratives, key=lambda x: len(x["text"].split(" ")))
        # add the first narrative to each batch
        for i in range(n):
            split[i].append(narratives[0])
        narratives = narratives[1:]
        for i, narrative in enumerate(narratives):
            split[i % n].append(narrative)

        for i, batch in enumerate(split):
            first = batch[0]
            others = batch[1:]
            random.shuffle(others)
            combo = [first] + others
            split[i] = combo[: self.batch_size]
            length = 0
            for narrative in split[i]:
                length += len(narrative["text"].split(" "))
            
            print(f"batch {i} has a total of {length} tokens")
        return split[: self.num_batches]

    def retrieve_uncompleted_batches(self) -> list or None:
        conn = DBUtils.create_connection(db_file=self.db)
        rows = DBUtils.return_query(
            "SELECT DISTINCT Batch_ID FROM Batch_ID_to_Narrative_ID WHERE Batch_ID NOT IN (SELECT DISTINCT Batch_ID FROM Completed_narratives)",
            conn,
        )
        return [row[0] for row in rows]

    def retrieve_batches(self) -> list:
        conn = DBUtils.create_connection(db_file=self.db)
        rows = DBUtils.return_query(
            "SELECT DISTINCT Batch_ID FROM Batch_ID_to_Narrative_ID", conn
        )
        # remove duplicates
        conn.close()
        if len(rows) == 0:
            return None
        return list(set([row[0] for row in rows]))

    def insert_batches(self, batches: list) -> None:
        conn = DBUtils.create_connection(db_file=self.db)
        for i, batch in enumerate(batches):
            # print (i)
            for narrative in batch:
                DBUtils.insert_row(
                    table="Batch_ID_to_Narrative_ID",
                    fields=["Batch_ID", "Narrative_ID"],
                    values=[i, narrative["id"]],
                    conn=conn,
                )
        conn.close()

    def assign_batch_to_cookie(self, cookie: str, batch: int) -> None:
        conn = DBUtils.create_connection(db_file=self.db)
        DBUtils.insert_row(
            "Batch_ID_to_Cookie", ["Batch_ID", "Cookie"], [batch, cookie], conn
        )
        conn.close()

    def retrieve_batch_from_cookie(self, cookie: str) -> int or None:
        conn = DBUtils.create_connection(db_file=self.db)
        rows = DBUtils.select_rows(
            "Batch_ID_to_Cookie", ["Batch_ID"], "Cookie=?", [cookie], conn
        )
        conn.close()
        if len(rows) == 0:
            return None
        return rows[0][0]

    def retrieve_unassigned_batches(self) -> list or None:
        conn = DBUtils.create_connection(db_file=self.db)
        rows = DBUtils.return_query(
            "SELECT DISTINCT Batch_ID FROM Batch_ID_to_Narrative_ID WHERE Batch_ID NOT IN (SELECT DISTINCT Batch_ID FROM Batch_ID_to_Cookie)",
            conn,
        )
        return [row[0] for row in rows]

    def retrieve_narratives_from_batch(self, batch: int) -> list or None:
        conn = DBUtils.create_connection(db_file=self.db)
        rows = DBUtils.select_rows(
            "Batch_ID_to_Narrative_ID", ["Narrative_ID"], "Batch_ID=?", [batch], conn
        )
        conn.close()
        ids = [row[0] for row in rows]
        if len(ids) == 0:
            return None
        return ids

    def retrieve_narrative_from_id(self, id: str) -> str or None:
        conn = DBUtils.create_connection(db_file=self.db)
        rows = DBUtils.select_rows(
            "Narrative_ID_to_Narrative_data",
            ["Narrative_data"],
            "Narrative_ID=?",
            [id],
            conn,
        )
        conn.close()
        if len(rows) == 0:
            return None
        return rows[0][0]

    def retrieve_all_cookies(self) -> list:
        conn = DBUtils.create_connection(db_file=self.db)
        rows = DBUtils.return_query(
            "SELECT DISTINCT Cookie FROM Cookie_to_Prolific_ID", conn
        )
        conn.close()
        if len(rows) == 0:
            return None
        return [row[0] for row in rows]

    def retrieve_cookie_from_prolific_id(self, prolific_id: str) -> str or None:
        conn = DBUtils.create_connection(db_file=self.db)
        rows = DBUtils.select_rows(
            "Cookie_to_Prolific_ID", ["Cookie"], "Prolific_ID=?", [prolific_id], conn
        )
        conn.close()
        if len(rows) == 0:
            return None
        return rows[0][0]

    def track_completion(
        self,
        cookie: str,
        current_narrative: str,
        completion_data: str,
        time: datetime.time,
    ) -> None:
        # if already completed, update
        # print (cookie, current_narrative, completion_data, time)
        conn = DBUtils.create_connection(db_file=self.db)
        if (
            len(
                DBUtils.select_rows(
                    "Completed_narratives",
                    ["Narrative_ID"],
                    "Cookie=? AND Narrative_ID=?",
                    [cookie, current_narrative],
                    conn,
                )
            )
            > 0
        ):
            DBUtils.update_row(
                "Completed_narratives",
                ["Completion_data", "Narrative_completion_timestamp"],
                [completion_data, time],
                "Cookie=? AND Narrative_ID=?",
                [cookie, current_narrative],
                conn,
            )
        else:
            DBUtils.insert_row(
                "Completed_narratives",
                [
                    "Cookie",
                    "Narrative_ID",
                    "Completion_data",
                    "Narrative_completion_timestamp",
                ],
                [cookie, current_narrative, completion_data, time],
                conn,
            )
        conn.close()

    def retrieve_completed_narratives(self, cookie: str) -> list:
        conn = DBUtils.create_connection(db_file=self.db)
        rows = DBUtils.select_rows(
            "Completed_narratives", ["Narrative_ID"], "Cookie=?", [cookie], conn
        )
        conn.close()
        if rows is None:
            return []
        return [row[0] for row in rows]

    def retrieve_uncompleted_narratives(self, cookie: str) -> list:
        conn = DBUtils.create_connection(db_file=self.db)
        batch = DBUtils.select_rows(
            "Batch_ID_to_Cookie", ["Batch_ID"], "Cookie=?", [cookie], conn=conn
        )
        all_narratives = DBUtils.select_rows(
            "Batch_ID_to_Narrative_ID",
            ["Narrative_ID"],
            "Batch_ID=?",
            [batch[0][0]],
            conn,
        )
        completed = DBUtils.select_rows(
            "Completed_narratives", ["Narrative_ID"], "Cookie=?", [cookie], conn
        )
        conn.close()
        completed = [row[0] for row in completed]
        all_narratives = [row[0] for row in all_narratives]
        missing = [
            narrative for narrative in all_narratives if narrative not in completed
        ]
        return missing

    def assign_cookie(self, cookie: str, prolific_id: str, time: datetime.time) -> None:
        conn = DBUtils.create_connection(db_file=self.db)
        DBUtils.insert_row(
            table="Cookie_to_Prolific_ID",
            fields=["Cookie", "Prolific_ID", "First_accessed_timestamp"],
            values=[cookie, prolific_id, time],
            conn=conn,
        )
        conn.close()

    def retrieve_prolific_id_from_cookie(self, cookie: str) -> str or None:
        conn = DBUtils.create_connection(db_file=self.db)
        rows = DBUtils.select_rows(
            "Cookie_to_Prolific_ID", ["Prolific_ID"], "Cookie=?", [cookie], conn
        )
        conn.close()
        if len(rows) == 0:
            return None
        return rows[0][0]

    def generate_completion_code(self, cookie: str, time: datetime.time) -> str:
        batch_id = self.retrieve_batch_from_cookie(cookie)
        if self.completion_code:
            return self.completion_code
        conn = DBUtils.create_connection(db_file=self.db)
        result = None
        while result is None:
            try:
                code = "".join(
                    random.choices(string.ascii_uppercase + string.digits, k=10)
                )
                # connect
                result = DBUtils.insert_row(
                    table="Completion_codes",
                    fields=[
                        "Cookie",
                        "Batch_ID",
                        "Completion_code",
                        "Completion_timestamp",
                    ],
                    values=[cookie, batch_id, code, time],
                    conn=conn,
                )
            except sqlite3.IntegrityError:
                pass
        conn.close()
        return code

    def retrieve_completion_code(self, cookie: str) -> str or None:
        if self.completion_code:
            return self.completion_code
        batch_id = self.retrieve_batch_from_cookie(cookie)
        conn = DBUtils.create_connection(db_file=self.db)
        rows = DBUtils.select_rows(
            "Completion_codes",
            ["Completion_code"],
            "Cookie=? AND Batch_ID=?",
            [cookie, batch_id],
            conn,
        )
        conn.close()
        if len(rows) == 0:
            return None
        return rows[0][0]

    def retrieve_elicitation_from_id_cookie(self, id: str, cookie: str) -> str or None:
        conn = DBUtils.create_connection(db_file=self.db)
        rows = DBUtils.select_rows(
            "Completed_narratives",
            ["Completion_data"],
            "Narrative_ID=? AND Cookie=?",
            [id, cookie],
            conn,
        )
        conn.close()
        if len(rows) == 0:
            return None
        return rows[0][0]

    def expire_cookie(self, cookie: str) -> None:
        conn = DBUtils.create_connection(db_file=self.db)
        DBUtils.insert_row("Expired_Cookie", ["Cookie"], [cookie], conn)
        conn.close()

    def check_if_expired(self, cookie: str) -> bool:
        conn = DBUtils.create_connection(db_file=self.db)
        rows = DBUtils.select_rows(
            "Expired_Cookie", ["Cookie"], "Cookie=?", [cookie], conn
        )
        conn.close()
        if len(rows) == 0:
            return False
        return True

    def retrieve_first_narrative_timestamp(self, cookie: str) -> datetime.time or None:
        conn = DBUtils.create_connection(db_file=self.db)
        rows = DBUtils.select_rows(
            "Cookie_to_Prolific_ID",
            ["First_narrative_timestamp"],
            "Cookie=?",
            [cookie],
            conn,
        )
        conn.close()
        if len(rows) == 0:
            return None
        return rows[0][0]

    def insert_first_narrative_timestamp(
        self, cookie: str, time: datetime.time
    ) -> None:
        conn = DBUtils.create_connection(db_file=self.db)
        DBUtils.update_row(
            "Cookie_to_Prolific_ID",
            ["First_narrative_timestamp"],
            [time],
            "Cookie=?",
            [cookie],
            conn,
        )
        conn.close()

    def track_example(
        self, cookie: str, form_id: str, example: str, time: datetime.time
    ) -> None:
        conn = DBUtils.create_connection(db_file=self.db)
        # print(f"example {example}")
        rows = DBUtils.select_rows(
            "Example_ID_to_Cookie",
            ["Cookie", "Example_ID"],
            "Cookie=? AND Example_ID=?",
            [cookie, form_id],
            conn,
        )
        if len(rows) > 0:
            DBUtils.update_row(
                "Example_ID_to_Cookie",
                ["Example_ID", "Example_answer", "Timestamp"],
                [form_id, example, time],
                "Cookie=?",
                [cookie],
                conn,
            )
        else:
            DBUtils.insert_row(
                "Example_ID_to_Cookie",
                ["Cookie", "Example_ID", "Example_answer", "Timestamp"],
                [cookie, form_id, example, time],
                conn,
            )
        conn.close()

    def retrieve_all(self, cookie: str):
        conn = DBUtils.create_connection(db_file=self.db)
        # retrieve prolific ID
        rows = DBUtils.select_rows(
            "Cookie_to_Prolific_ID", ["Prolific_ID"], "Cookie=?", [cookie], conn
        )
        if len(rows) == 0:
            return None
        prolific_id = rows[0][0]
        # retrieve times
        rows = DBUtils.select_rows(
            "Cookie_to_Prolific_ID",
            ["First_accessed_timestamp", "First_narrative_timestamp"],
            "Cookie=?",
            [cookie],
            conn,
        )
        if len(rows) == 0:
            return None
        first_accessed_timestamp = rows[0][0]
        first_narrative_timestamp = rows[0][1]
        # retrieve each narrative
        rows = DBUtils.select_rows(
            "Completed_narratives",
            ["Narrative_ID", "Completion_data", "Narrative_completion_timestamp"],
            "Cookie=?",
            [cookie],
            conn,
        )
        if len(rows) == 0:
            return None
        narrative_ids = [row[0] for row in rows]
        completion_data = [row[1] for row in rows]
        completion_timestamp = [row[2] for row in rows]
        # retrieve narratives
        rows = DBUtils.select_rows(
            "Narrative_ID_to_Narrative_data",
            ["Narrative_ID", "Narrative_data"],
            "Narrative_ID IN ({})".format(",".join("?" for _ in narrative_ids)),
            narrative_ids,
            conn,
        )
        if len(rows) == 0:
            return None
        narratives = [row[1] for row in rows]
        narratives = [json.loads(narrative) for narrative in narratives]
        # retrieve completion timestamp
        # rows = DBUtils.select_rows("Completion_codes", ["Completion_timestamp"], "Cookie=?", [cookie], conn)
        # if len(rows) == 0:
        #     return None
        # retrieve example answers
        rows = DBUtils.select_rows(
            "Example_ID_to_Cookie",
            ["Example_ID", "Example_answer", "Timestamp"],
            "Cookie=?",
            [cookie],
            conn,
        )
        if len(rows) == 0:
            return None
        answers = {row[0]: row[1] for row in rows}
        completion_times = [row[2] for row in rows]
        data = {}
        data["answers"] = answers
        data["example_completion_times"] = completion_times
        data["prolific_id"] = prolific_id
        data["cookie"] = cookie
        data["first_accessed_timestamp"] = first_accessed_timestamp
        data["first_narrative_timestamp"] = first_narrative_timestamp
        data["narratives"] = []
        for id, completion_data, completion_timestamp in zip(
            narrative_ids, completion_data, completion_timestamp
        ):
            narrative = next(x for x in narratives if x["id"] == id)
            data["narratives"].append(
                {
                    "narrative_id": id,
                    "narrative": narrative,
                    "completion_data": completion_data,
                    "completion_timestamp": completion_timestamp,
                }
            )
        data["completion_time"] = completion_timestamp
        return data

    def retrieve_all_completed_narratives(self):
        conn = DBUtils.create_connection(db_file=self.db)
        rows = DBUtils.return_query(
            "SELECT DISTINCT Narrative_ID FROM Completed_narratives", conn
        )
        conn.close()
        if len(rows) == 0:
            return []
        return [row[0] for row in rows]
