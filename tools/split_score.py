import csv
import os
import re

input_file = "data/raw/fbref_all_matches/fbref_all_matches_1888_1950.csv"
output_file = "data/raw/fbref_all_matches/fbref_all_matches_1888_1950_split.csv"

def split_score_column():
    if not os.path.exists(input_file):
        print(f"Lỗi: Không tìm thấy file: {input_file}")
        return

    print("Đang cấu trúc lại file CSV: Tách cột Score thành HomeScore và AwayScore...")
    
    with open(input_file, 'r', encoding='utf-8') as fin, \
         open(output_file, 'w', encoding='utf-8', newline='') as fout:
        
        reader = csv.reader(fin)
        writer = csv.writer(fout)

        header = next(reader)
        expected_cols = len(header)
        
        # Tìm vị trí cột Score
        score_idx = -1
        for i, col in enumerate(header):
            if 'score' in col.lower() or 'result' in col.lower():
                score_idx = i
                break
        
        if score_idx == -1:
            print("Lỗi: Không tìm thấy cột Score/Result. Co the file nay da duoc tach roi!")
            return

        # Tạo Header mới
        new_header = header[:score_idx] + ['HomeScore', 'AwayScore'] + header[score_idx+1:]
        writer.writerow(new_header)

        split_comma_count = 0
        split_dash_count = 0
        empty_count = 0
        
        for row in reader:
            # 1. Xử lý dòng bị lỗi lưu "1,1" dẫn đến dư 1 cột
            if len(row) == expected_cols + 1:
                home_score = row[score_idx].strip()
                away_score = row[score_idx + 1].strip()
                new_row = row[:score_idx] + [home_score, away_score] + row[score_idx+2:]
                writer.writerow(new_row)
                split_comma_count += 1
                
            # 2. Xử lý dòng bình thường
            elif len(row) == expected_cols:
                score_val = row[score_idx].strip()
                
                # Regex MỚI: Bắt TẤT CẢ các loại dấu gạch (-, –, —) hoặc dấu hai chấm
                match = re.search(r'(\d+)\s*[-–—:,]\s*(\d+)', score_val)
                if match:
                    home_score = match.group(1)
                    away_score = match.group(2)
                    split_dash_count += 1
                else:
                    # Trận chưa đá, bị hoãn (VD: Postponed)
                    home_score = score_val 
                    away_score = ""
                    empty_count += 1
                    
                new_row = row[:score_idx] + [home_score, away_score] + row[score_idx+1:]
                writer.writerow(new_row)
            else:
                continue # Bỏ qua dòng rác
                
    print(f"\n✅ Đã tái cấu trúc xong!")
    print(f"   - Tách từ lỗi dấu phẩy (x,y): {split_comma_count} trận")
    print(f"   - Tách từ dấu gạch ngang (x-y, x–y): {split_dash_count} trận")
    print(f"   - Không có tỉ số rõ ràng (chưa đá): {empty_count} trận")
    print(f"👉 File chuẩn đã lưu tại: {output_file}")

if __name__ == "__main__":
    split_score_column()