import pandas as pd
import os

def merge_logos_to_original():
    file_goc = "data/raw/fbref_all_clubs_1.csv"
    file_logo = "data/raw/fbref_clubs_with_logos_final.csv"
    file_output = "data/raw/fbref_all_clubs_complete.csv"

    if not os.path.exists(file_goc) or not os.path.exists(file_logo):
        print("Loi: Khong tim thay file.")
        return

    print("Dang doc du lieu...")
    
    # 1. Doc file goc (co tieu de)
    df_original = pd.read_csv(file_goc)
    df_original.columns = df_original.columns.str.strip()

    # 2. Doc file logo (KHONG co tieu de - Dua tren anh image_65a91d.jpg)
    # Chung ta se tu dat ten cot cho no
    try:
        df_logo = pd.read_csv(file_logo, header=None, names=['ClubID', 'ClubName', 'LogoURL', 'Country'])
    except Exception as e:
        print(f"Loi khi doc file logo: {e}")
        return

    print(f"Da nhan dang duoc file logo. So luong dong: {len(df_logo)}")

    # 3. Lam sach du lieu de gop
    df_logo['ClubID'] = df_logo['ClubID'].astype(str).str.strip()
    df_original['ClubID'] = df_original['ClubID'].astype(str).str.strip()

    # Lay duy nhat LogoURL tuong ung voi ClubID de tranh lam phinh du lieu
    df_logo_clean = df_logo[['ClubID', 'LogoURL']].drop_duplicates(subset=['ClubID'])

    print(f"Dang gop logo vao {len(df_original)} doi bong...")

    # 4. Thuc hien merge
    df_final = pd.merge(df_original, df_logo_clean, on='ClubID', how='left')

    # Dua cot LogoURL len canh ClubName cho de nhin
    cols = df_final.columns.tolist()
    if 'LogoURL' in cols and 'ClubName' in cols:
        name_idx = cols.index('ClubName')
        cols.insert(name_idx + 1, cols.pop(cols.index('LogoURL')))
        df_final = df_final[cols]

    # 5. Luu file ket qua
    os.makedirs(os.path.dirname(file_output), exist_ok=True)
    df_final.to_csv(file_output, index=False, encoding='utf-8-sig')

    print("-" * 30)
    print(f"Hoan thanh! File moi: {file_output}")
    print(f"So doi da co Logo: {df_final['LogoURL'].notna().sum()} / {len(df_final)}")
    print("-" * 30)

if __name__ == "__main__":
    merge_logos_to_original()