import csv
import os

input_file = "data/raw/fbref_all_matches/fbref_all_matches_2025.csv"
output_file = "data/raw/fbref_all_matches/fbref_all_matches_2025_fixed.csv"

def fix_score_comma():
    if not os.path.exists(input_file):
        print(f"Không tìm thấy file: {input_file}")
        return

    print(f"Đang sửa lỗi dấu phẩy trong cột tỉ số...")
    
    with open(input_file, 'r', encoding='utf-8') as fin, \
         open(output_file, 'w', encoding='utf-8', newline='') as fout:
        
        reader = csv.reader(fin)
        writer = csv.writer(fout)

        # Lấy Header và tìm vị trí cột Score
        header = next(reader)
        writer.writerow(header)
        expected_cols = len(header)
        
        score_idx = -1
        for i, col in enumerate(header):
            if 'score' in col.lower() or 'result' in col.lower():
                score_idx = i
                break
        
        if score_idx == -1:
            print("Lỗi: Không tìm thấy cột Score (hoặc Result) trong file của bạn!")
            return

        fixed_count = 0
        normal_count = 0
        
        for row in reader:
            # Nếu dòng bị dư đúng 1 cột (12 cột)
            if len(row) == expected_cols + 1:
                # Gộp 2 phần của tỉ số lại thành '1-1'
                part1 = row[score_idx].strip()
                part2 = row[score_idx + 1].strip()
                fixed_score = f"{part1}-{part2}"
                
                # Cắt ghép lại dòng dữ liệu
                fixed_row = row[:score_idx] + [fixed_score] + row[score_idx+2:]
                writer.writerow(fixed_row)
                fixed_count += 1
            else:
                writer.writerow(row)
                normal_count += 1
                
    print(f"✅ Đã dọn dẹp xong!")
    print(f"   - Số trận bình thường: {normal_count}")
    print(f"   - Số trận đã sửa tỉ số (từ 'x,y' thành 'x-y'): {fixed_count}")
    print(f"File sạch đã lưu tại: {output_file}")

if __name__ == "__main__":
    fix_score_comma()