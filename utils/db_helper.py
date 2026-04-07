# Kết nối MySQL (của dự án Laravel)
import mysql.connector
import pandas as pd
import os

def test_connection_and_import():
    # Cấu hình Database (Thường giống với file .env trong Laravel)
    db_config = {
        'host': '127.0.0.1',
        'user': 'root',           # User mặc định của XAMPP/Laragon
        'password': '',           # Pass mặc định thường để trống
        'database': 'ai_soccer'   # Tên database dự án của bạn
    }

    try:
        # --- BƯỚC 1: KIỂM TRA KẾT NỐI ---
        print("⏳ Đang thử kết nối MySQL...")
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        print("✅ Kết nối Database thành công!")

        # --- BƯỚC 2: TẠO BẢNG TẠM ---
        # Tạo một bảng để chứa raw data. 
        # Sau này bạn có thể dùng Migration của Laravel để thiết kế lại bảng chuẩn hơn.
        create_table_query = """
        CREATE TABLE IF NOT EXISTS raw_matches (
            id INT AUTO_INCREMENT PRIMARY KEY,
            round VARCHAR(50),
            match_date VARCHAR(50),
            home_team VARCHAR(100),
            away_team VARCHAR(100),
            home_score INT,
            away_score INT
        )
        """
        cursor.execute(create_table_query)
        print("✅ Đã kiểm tra/tạo bảng 'raw_matches'.")

        # Xóa dữ liệu cũ trong bảng để tránh trùng lặp khi chạy test nhiều lần
        cursor.execute("TRUNCATE TABLE raw_matches")

        # --- BƯỚC 3: ĐỌC CSV VÀ IMPORT ---
        csv_path = "data/raw/match_results.csv"
        if not os.path.exists(csv_path):
            print(f"❌ Không tìm thấy file {csv_path}. Hãy chạy file cào dữ liệu trước.")
            return

        print("⏳ Đang đọc file CSV và làm sạch dữ liệu...")
        df = pd.read_csv(csv_path)

        # MÀNG LỌC BẢO VỆ: Ép kiểu dữ liệu
        # errors='coerce' sẽ biến tất cả những đoạn chữ rác (như 'igi') thành NaN (Not a Number)
        df['HomeScore'] = pd.to_numeric(df['HomeScore'], errors='coerce')
        df['AwayScore'] = pd.to_numeric(df['AwayScore'], errors='coerce')
        
        # Xóa thẳng tay những dòng bị NaN (những dòng chứa rác)
        df = df.dropna(subset=['HomeScore', 'AwayScore'])

        # Chuẩn bị câu lệnh Insert
        insert_query = """
        INSERT INTO raw_matches (round, match_date, home_team, away_team, home_score, away_score)
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        # Chuyển DataFrame thành danh sách các Tuple
        data_to_insert = []
        for _, row in df.iterrows():
            data_to_insert.append((
                str(row['Round']),
                str(row['Date']),
                str(row['Home']),
                str(row['Away']),
                int(row['HomeScore']), # Lúc này chắc chắn 100% nó là số
                int(row['AwayScore'])
            ))

        # Thực thi Insert hàng loạt
        cursor.executemany(insert_query, data_to_insert)
        conn.commit() # Lưu thay đổi vào DB

        print(f"\n🎉 THÀNH CÔNG RỰC RỠ! Đã lưu {cursor.rowcount} trận đấu sạch vào database '{db_config['database']}'.")

        print("⏳ Đang đọc file CSV và đẩy vào Database...")
        df = pd.read_csv(csv_path)

        # Chẩn bị câu lệnh Insert
        insert_query = """
        INSERT INTO raw_matches (round, match_date, home_team, away_team, home_score, away_score)
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        # Chuyển DataFrame thành danh sách các Tuple để chạy executemany cho nhanh
        data_to_insert = []
        for _, row in df.iterrows():
            data_to_insert.append((
                str(row['Round']),
                str(row['Date']),
                str(row['Home']),
                str(row['Away']),
                int(row['HomeScore']),
                int(row['AwayScore'])
            ))

        # Thực thi Insert hàng loạt
        cursor.executemany(insert_query, data_to_insert)
        conn.commit() # Lưu thay đổi vào DB

        print(f"\n🎉 THÀNH CÔNG RỰC RỠ! Đã lưu {cursor.rowcount} trận đấu vào database '{db_config['database']}'.")

    except mysql.connector.Error as err:
        print(f"\n❌ Lỗi MySQL: {err}")
        print("💡 Gợi ý: Kiểm tra xem XAMPP/Laragon đã bật MySQL chưa, hoặc sai mật khẩu/tên database.")
    except Exception as e:
        print(f"\n💥 Lỗi hệ thống: {e}")
    finally:
        # Đóng kết nối để giải phóng tài nguyên
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
            print("🧹 Đã ngắt kết nối an toàn.")

if __name__ == "__main__":
    test_connection_and_import()