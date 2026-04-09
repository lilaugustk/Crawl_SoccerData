import pandas as pd
import os

def merge_club_logos():
    file_cu = "data/raw/fbref_all_clubs_1.csv"
    file_moi = "data/raw/fbref_all_clubs_with_logos_2.csv" # Hoac v3 tuy ten ban dat
    file_output = "data/raw/fbref_all_clubs.csv"

    if not os.path.exists(file_cu) or not os.path.exists(file_moi):
        print("Loi: Khong tim thay mot trong hai file de gop.")
        return

    print("Dang doc du lieu...")
    df_cu = pd.read_csv(file_cu)
    df_moi = pd.read_csv(file_moi)

    # Chi lay 2 cot can thiet tu file moi de gop: ClubID de lam key va LogoURL
    # Loai bo cac dong trung lap trong file moi truoc khi gop
    df_logos = df_moi[['ClubID', 'LogoURL']].drop_duplicates(subset=['ClubID'])

    print(f"Dang gop Logo cho {len(df_cu)} doi bong...")
    
    # Dung merge voi how='left' de giu nguyen tat ca doi o file cu
    df_final = pd.merge(df_cu, df_logos, on='ClubID', how='left')

    # Luu file ket qua
    df_final.to_csv(file_output, index=False, encoding='utf-8-sig')
    
    print(f"Hoan thanh! Da tao file moi tai: {file_output}")
    print(f"So luong dong: {len(df_final)}")
    print("Cot hien tai:", df_final.columns.tolist())

if __name__ == "__main__":
    merge_club_logos()