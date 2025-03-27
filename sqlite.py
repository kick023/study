import sqlite3
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional


#  数据库初始化与表的创建
def init_database(db_name: str = "crypto_trades.db") -> sqlite3.Connection:
    """
    初始化数据库并创建交易记录表
    Args:  db_name: 数据库文件名
    Returns: sqlite3 连接对象
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # 创建交易表（包含关键业务字段 在其中有标注）
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS crypto_trades (
        trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,                 -- 交易时间
        trade_type TEXT CHECK(trade_type IN ('买入', '卖出')),  -- 交易类型
        pair TEXT NOT NULL,                      -- 交易对(BTC/USDT)
        quantity REAL NOT NULL,                  -- 交易数量
        price REAL NOT NULL,                     -- 成交单价
        platform TEXT CHECK(platform IN ('币安', 'bitget', 'OKX')),  -- 交易平台
        fee REAL DEFAULT 0.0,                    -- 手续费
        profit REAL                              -- 利润(卖出时计算)
    )
    """
    cursor.execute(create_table_sql)
    conn.commit()
    return conn


#  生成模拟数据
def generate_mock_data(num: int = 10) -> List[tuple]:
    """
    生成虚拟货币交易模拟数据
    num: 需要生成的数据条数 这里设置十条
    Returns:包含元组数据的列表，可以直接用于 SQL 插入
    """
    mock_data = []
    pairs = ["BTC/USDT", "ETH/USDT", "SOL/BTC"]
    platforms = ["币安", "bitget", "OKX"]

    for _ in range(num):
        # 生成时间（举例过去7天内，可以按自己需要的来）
        timestamp = datetime.now() - timedelta(
            days=random.randint(0, 7),
            hours=random.randint(0, 23)
        )
        timestamp = timestamp.isoformat()

        # 交易类型（买入时无利润不计算，只算卖掉的时候）
        trade_type = random.choice(["买入", "卖出"])
        pair = random.choice(pairs)
        base_coin = pair.split("/")[0]  # 例如 BTC

        # 生成价格和数量（不一样的币 用不同范围来 大概写点数进去）
        if "BTC" in pair:
            price = round(random.uniform(20000, 30000), 2)
            quantity = round(random.uniform(0.01, 1), 4)
        elif "ETH" in pair:
            price = round(random.uniform(1500, 2500), 2)
            quantity = round(random.uniform(0.1, 10), 4)
        else:
            price = round(random.uniform(50, 200), 2)
            quantity = round(random.uniform(1, 100), 2)

        # 手续费（按交易金额的%计算，随便写的百分之几 大概就行）
        fee = round(price * quantity * random.uniform(0.001, 0.003), 4)

        # 利润（仅在卖出时计算，买入哪来的利润）
        profit = round((price - random.uniform(price * 0.8, price * 1.2)) * quantity - fee, 2) \
            if trade_type == "卖出" else None #只算卖出的时候

        mock_data.append((
            timestamp,
            trade_type,
            pair,
            quantity,
            price,
            random.choice(platforms),
            fee,
            profit
        ))
    return mock_data


#  数据插入
def insert_trades(conn: sqlite3.Connection, data: List[tuple]) -> None:
    """
    批量插入交易记录
    conn: 数据库连接
    data: 从 generate_mock_data 生成的模拟数据 想要几条可以自己去设置
    """
    sql = """
    INSERT INTO crypto_trades 
    (timestamp, trade_type, pair, quantity, price, platform, fee, profit)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    try:
        conn.executemany(sql, data)
        conn.commit()
        print(f"成功插入 {len(data)} 条交易记录")
    except sqlite3.Error as e:
        print(f"插入失败: {e}")
        conn.rollback()


#  数据查询
def get_trade_by_id(conn: sqlite3.Connection, trade_id: int) -> Optional[Dict]:
    """
    根据 trade_id 获取单条交易详情conn: 数据库连接
        trade_id: 交易记录的唯一ID
    Returns:字典形式的数据记录，找不到的时候返回 None
    """
    sql = "SELECT * FROM crypto_trades WHERE trade_id = ?"
    cursor = conn.execute(sql, (trade_id,))
    row = cursor.fetchone()

    if row:
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
    return None


def get_trades_by_condition(
        conn: sqlite3.Connection,
        conditions: Dict[str, str],
        limit: int = 5
) -> List[Dict]:
    """
    根据条件查询多条交易记录
        conn: 数据库连接
        conditions: 查询条件字典，比如说{"platform": "币安", "trade_type": "买入"}
        limit: 返回结果的最大数量
    Returns:包含字典记录的列表
    """
    # 动态构建查询语句如下
    where_clause = " AND ".join([f"{k} = ?" for k in conditions.keys()])
    sql = f"SELECT * FROM crypto_trades WHERE {where_clause} LIMIT ?"

    # 准备参数
    params = list(conditions.values()) + [limit]

    cursor = conn.execute(sql, params)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


# 数据更新 把新的替换进去
def update_trade_field(
        conn: sqlite3.Connection,
        trade_id: int,
        field: str,
        new_value: str | float
) -> bool:
    """
    更新指定交易的字段值
        conn: 数据库连接
        trade_id: 要修改的交易ID
        field: 要修改的字段名（要存表中的）
        new_value: 新的字段值
    Returns:是否更新成功
    """
    # 安全校验，防止 SQL 注入
    allowed_fields = ["trade_type", "pair", "quantity", "price", "platform", "fee", "profit"]
    if field not in allowed_fields:
        print(f"错误，不允许修改字段 {field}")
        return False

    sql = f"UPDATE crypto_trades SET {field} = ? WHERE trade_id = ?"
    try:
        conn.execute(sql, (new_value, trade_id))
        conn.commit()
        print(f"成功更新交易 {trade_id} 的 {field} 字段")
        return True
    except sqlite3.Error as e:
        print(f"更新失败: {e}")
        conn.rollback()
        return False


# 使用（示例）
if __name__ == "__main__":
    # 初始化数据库
    conn = init_database()

    # 插入模拟数据（如果表为空）
    if conn.execute("SELECT COUNT(*) FROM crypto_trades").fetchone()[0] == 0:
        mock_data = generate_mock_data()
        insert_trades(conn, mock_data)

    # 查询单条记录
    print("\n *** 查询单条交易 ***")
    trade = get_trade_by_id(conn, 1)
    print(trade)

    # 条件查询（例如平台为'币安'的买入记录）
    print("\n *** 条件查询 ***")
    condition_trades = get_trades_by_condition(
        conn,
        {"platform": "币安", "trade_type": "买入"},
        limit=3
    )
    for t in condition_trades:
        print(f"[交易ID:{t['trade_id']}] {t['pair']} 数量:{t['quantity']}")

    # 更新手续费（也可以是其他 看自己需要改哪儿）字段
    print("\n *** 更新数据 ***")
    success = update_trade_field(conn, 1, "fee", 0.00000001)
    if success:
        updated_trade = get_trade_by_id(conn, 1)
        print(f"更新后的手续费: {updated_trade['fee']}")

    # 关闭连接
    conn.close()