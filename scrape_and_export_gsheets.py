import os
import sys
import json
import re
import datetime
import hashlib
import urllib.request
import urllib.parse
import subprocess
import requests

def get_google_access_token():
    # 1. First check direct environment variables (used by GitHub Actions Secrets)
    client_id = os.environ.get("GOOGLE_WORKSPACE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_WORKSPACE_CLIENT_SECRET")
    refresh_token = os.environ.get("GOOGLE_WORKSPACE_REFRESH_TOKEN")
    
    # 2. Fallback to local config file if running on local Mac
    if not (client_id and client_secret and refresh_token):
        gws_env_path = os.path.expanduser("~/.config/gws/gws_env.sh")
        if os.path.exists(gws_env_path):
            cmd = f"source {gws_env_path} && python3 -c \"import os, json; print(json.dumps({{k: os.environ[k] for k in ['GOOGLE_WORKSPACE_CLIENT_ID', 'GOOGLE_WORKSPACE_CLIENT_SECRET', 'GOOGLE_WORKSPACE_REFRESH_TOKEN'] if k in os.environ}}))\""
            out = subprocess.check_output(["bash", "-c", cmd]).decode()
            env_vars = json.loads(out)
            client_id = env_vars.get("GOOGLE_WORKSPACE_CLIENT_ID")
            client_secret = env_vars.get("GOOGLE_WORKSPACE_CLIENT_SECRET")
            refresh_token = env_vars.get("GOOGLE_WORKSPACE_REFRESH_TOKEN")
            
    if not (client_id and client_secret and refresh_token):
        raise ValueError("Missing Google Workspace credentials in environment or ~/.config/gws/gws_env.sh")
        
    token_url = "https://oauth2.googleapis.com/token"
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }).encode("utf-8")
    
    req = urllib.request.Request(token_url, data=data, method="POST")
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode())
        return res["access_token"]

def fetch_dmcl_ref_data():
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    vn_hour = (utc_now.hour + 7) % 24
    token = hashlib.md5(f"dmcl2026EDKSC{vn_hour:02d}".encode()).hexdigest()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "X-Api-Token": token,
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://dienmaycholon.com/tu-lanh"
    }
    
    # 1. Fetch subcategory filters
    subcats = {
        "Side by side": "t[]=side-by-side",
        "Tủ nhiều cửa": "t[]=tu-nhieu-cua",
        "Mini": "t[]=mini",
        "Ngăn đá trên": "t[]=ngan-da-tren",
        "Ngăn đá dưới": "t[]=ngan-da-duoi",
        "Tủ âm tường": "u[]=tu-am-tuong"
    }
    
    subcat_map = {}
    print("Fetching subcategory filters...")
    for sc_name, sc_param in subcats.items():
        u = f"https://dienmaycholon.com/api/product/cate?page=1&offset=200&id=18&{sc_param}"
        try:
            r = requests.get(u, headers=headers, timeout=20).json()
            if r.get("status") == 200:
                items = r.get("data", {}).get("data", [])
                for it in items:
                    subcat_map.setdefault(it["id"], []).append(sc_name)
                print(f"  Mapped {len(items)} items for {sc_name}")
        except Exception as e:
            print(f"  Error fetching {sc_name}: {e}")
            
    manual_subcats = {
        "tu-lanh-samsung-inverter-655-lit-rs70f65q3fsv": ["Side by side"],
        "tu-lanh-dreame-inverter-400-lit-drb400wgb3vn": ["Ngăn đá dưới"],
        "tu-lanh-dreame-inverter-400-lit-drb400wgw3vn": ["Ngăn đá dưới"],
        "tu-lanh-dreame-inverter-600-lit-drc600wgb4vn": ["Tủ nhiều cửa"]
    }
    
    # 2. Fetch all products (Category ID 18 = Tu lanh)
    print("Fetching complete product catalog for REF (Category ID 18)...")
    url_all = "https://dienmaycholon.com/api/product/cate?page=1&offset=300&id=18"
    resp = requests.get(url_all, headers=headers, timeout=30).json()
    all_items = resp.get("data", {}).get("data", [])
    print(f"Total raw items fetched: {len(all_items)}")
    
    extracted_rows = []
    
    for it in all_items:
        pid = it.get("id")
        alias = it.get("alias", "")
        code = it.get("code") or ""
        name = it.get("name") or ""
        
        # Sub CAT
        sc_list = subcat_map.get(pid, [])
        if not sc_list and alias in manual_subcats:
            sc_list = manual_subcats[alias]
        sub_cat_str = ", ".join(sc_list) if sc_list else "Khác"
        
        # Status
        fi = it.get("flag_index", {}) or {}
        fc = it.get("flag_content", {}) or {}
        is_biz = fi.get("is_business")
        no_biz = fi.get("no_business")
        model_year = fc.get("model")
        is_new = fi.get("is_product_new") == "1" or fi.get("is_product_new_cate") == 1 or model_year == "2026"
        is_rumor = fi.get("is_rumor") == "1"
        
        if is_biz == "0" or is_biz is None or no_biz == "1":
            status_str = "Sản phẩm bỏ mẫu"
        elif is_new:
            status_str = "Sản phẩm mới"
        elif is_rumor:
            status_str = "Hàng sắp về"
        else:
            status_str = "Đang kinh doanh"
            
        direct_link = f"https://dienmaycholon.com/tu-lanh/{alias}" if alias else ""
        
        # MRP price
        raw_mrp = it.get("saleprice")
        try:
            mrp_price = int(raw_mrp) if raw_mrp else 0
        except:
            mrp_price = 0
            
        # Selling price
        raw_disc = it.get("discount")
        try:
            disc_price = int(raw_disc) if raw_disc else 0
        except:
            disc_price = 0
            
        is_sock = fi.get("is_sock") == "1"
        price_sock = fc.get("price_sock")
        try:
            psock_val = int(price_sock) if price_sock else 0
        except:
            psock_val = 0
            
        if it.get("is_promotion") == "0" and is_sock and psock_val > 0:
            selling_price = psock_val
        else:
            selling_price = disc_price
            
        if mrp_price == 0 and selling_price > 0:
            mrp_price = selling_price
            
        discount_pct = round((mrp_price - selling_price) / mrp_price, 4) if mrp_price > selling_price and mrp_price > 0 else 0
        
        # Promotions
        promo_texts = []
        gift_val = it.get("price_gift_text")
        if gift_val and int(gift_val) > 0:
            promo_texts.append(f"Quà tặng trị giá {int(gift_val):,}đ".replace(",", "."))
            
        pt = fc.get("promo_text", {})
        if isinstance(pt, dict):
            for k, v in pt.items():
                t = re.sub(r"<[^<]+?>", "", v.get("contentview", "")).strip()
                if t and t not in promo_texts:
                    promo_texts.append(t)
        elif isinstance(pt, list):
            for v in pt:
                t = re.sub(r"<[^<]+?>", "", v.get("contentview", "")).strip()
                if t and t not in promo_texts:
                    promo_texts.append(t)
                    
        promo_str = "\n".join(f"• {p}" for p in promo_texts) if promo_texts else "Không có khuyến mãi đặc biệt"
        
        extracted_rows.append({
            "cat": "REF",
            "sub_cat": sub_cat_str,
            "model": code,
            "name": name,
            "status": status_str,
            "direct_link": direct_link,
            "mrp_price": mrp_price,
            "selling_price": selling_price,
            "discount_pct": discount_pct,
            "promotion": promo_str
        })
        
    return extracted_rows

def sync_to_google_sheet(access_token, data_rows, spreadsheet_id=None):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Vietnam timestamp
    vn_tz = datetime.timezone(datetime.timedelta(hours=7))
    update_time_str = datetime.datetime.now(vn_tz).strftime("%d/%m/%Y %H:%M:%S")
    
    # 1. Create spreadsheet if not provided
    if not spreadsheet_id:
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        title = f"DMCL_REF_Price_Tracking_{today_str}"
        create_body = {
            "properties": {"title": title},
            "sheets": [
                {"properties": {"sheetId": 0, "title": "REF_Products", "gridProperties": {"frozenRowCount": 1}}},
                {"properties": {"sheetId": 1, "title": "Summary_Dashboard", "gridProperties": {"frozenRowCount": 1}}}
            ]
        }
        create_resp = requests.post("https://sheets.googleapis.com/v4/spreadsheets", headers=headers, json=create_body, timeout=30).json()
        spreadsheet_id = create_resp["spreadsheetId"]
        spreadsheet_url = create_resp["spreadsheetUrl"]
        print(f"Created new spreadsheet: {title}")
    else:
        spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
        print(f"Updating existing spreadsheet: {spreadsheet_id}")
        
    # 2. Prepare Data for REF_Products
    header_row = [
        "CAT",
        "Sub CAT",
        "Tên Model",
        "Tên Sản Phẩm",
        "Status",
        "Direct Product Link",
        "MRP Price (VNĐ)",
        "Selling Price (VNĐ)",
        "Discount %",
        "Thông Tin Khuyến Mãi"
    ]
    
    values = [header_row]
    for r in data_rows:
        values.append([
            r["cat"],
            r["sub_cat"],
            r["model"],
            r["name"],
            r["status"],
            r["direct_link"],
            r["mrp_price"],
            r["selling_price"],
            r["discount_pct"],
            r["promotion"]
        ])
        
    # Clear old data and write new
    clear_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/REF_Products!A1:J1000:clear"
    requests.post(clear_url, headers=headers, timeout=20)
    
    update_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/REF_Products!A1:J{len(values)}?valueInputOption=USER_ENTERED"
    requests.put(update_url, headers=headers, json={"values": values}, timeout=30)
    print(f"Updated REF_Products sheet with {len(data_rows)} rows.")
    
    # 3. Prepare Summary Dashboard
    subcat_stats = {}
    for r in data_rows:
        sc = r["sub_cat"]
        if sc not in subcat_stats:
            subcat_stats[sc] = {"count": 0, "prices": []}
        subcat_stats[sc]["count"] += 1
        if r["selling_price"] > 0:
            subcat_stats[sc]["prices"].append(r["selling_price"])
            
    summary_values = [
        ["BÁO CÁO TỔNG QUAN DANH MỤC TỦ LẠNH (REF) - SIÊU THỊ ĐIỆN MÁY CHỢ LỚN"],
        [f"Cập nhật lúc: {update_time_str}", "", "", "", f"Tổng số model: {len(data_rows)}"],
        [],
        ["Phân khúc / Sub CAT", "Số lượng Model", "Giá thấp nhất (VNĐ)", "Giá trung bình (VNĐ)", "Giá cao nhất (VNĐ)"]
    ]
    
    for sc, stat in sorted(subcat_stats.items(), key=lambda x: -x[1]["count"]):
        prices = stat["prices"]
        min_p = min(prices) if prices else 0
        max_p = max(prices) if prices else 0
        avg_p = int(sum(prices) / len(prices)) if prices else 0
        summary_values.append([sc, stat["count"], min_p, avg_p, max_p])
        
    summary_values.append([])
    summary_values.append(["Trạng thái kinh doanh", "Số lượng Model", "Tỷ trọng"])
    status_counts = {}
    for r in data_rows:
        st = r["status"]
        status_counts[st] = status_counts.get(st, 0) + 1
    for st, count in status_counts.items():
        summary_values.append([st, count, round(count / len(data_rows), 4)])
        
    clear_summary_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/Summary_Dashboard!A1:E100:clear"
    requests.post(clear_summary_url, headers=headers, timeout=20)
    
    update_summary_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/Summary_Dashboard!A1:E{len(summary_values)}?valueInputOption=USER_ENTERED"
    requests.put(update_summary_url, headers=headers, json={"values": summary_values}, timeout=30)
    print("Updated Summary_Dashboard sheet.")
    
    # 4. Apply styling with batchUpdate
    format_requests = [
        {
            "repeatCell": {
                "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 10},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.106, "green": 0.212, "blue": 0.365},
                        "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 10},
                        "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE", "wrapStrategy": "WRAP"
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,wrapStrategy)"
            }
        },
        {
            "repeatCell": {
                "range": {"sheetId": 0, "startRowIndex": 1, "endRowIndex": len(values), "startColumnIndex": 6, "endColumnIndex": 8},
                "cell": {"userEnteredFormat": {"numberFormat": {"type": "CURRENCY", "pattern": "#,##0 \"₫\""}, "horizontalAlignment": "RIGHT"}},
                "fields": "userEnteredFormat(numberFormat,horizontalAlignment)"
            }
        },
        {
            "repeatCell": {
                "range": {"sheetId": 0, "startRowIndex": 1, "endRowIndex": len(values), "startColumnIndex": 8, "endColumnIndex": 9},
                "cell": {"userEnteredFormat": {"numberFormat": {"type": "PERCENT", "pattern": "0.0%"}, "horizontalAlignment": "CENTER"}},
                "fields": "userEnteredFormat(numberFormat,horizontalAlignment)"
            }
        },
        {
            "repeatCell": {
                "range": {"sheetId": 0, "startRowIndex": 1, "endRowIndex": len(values), "startColumnIndex": 0, "endColumnIndex": 1},
                "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER"}},
                "fields": "userEnteredFormat(horizontalAlignment)"
            }
        },
        {
            "repeatCell": {
                "range": {"sheetId": 0, "startRowIndex": 1, "endRowIndex": len(values), "startColumnIndex": 4, "endColumnIndex": 5},
                "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER"}},
                "fields": "userEnteredFormat(horizontalAlignment)"
            }
        },
        {
            "repeatCell": {
                "range": {"sheetId": 0, "startRowIndex": 1, "endRowIndex": len(values), "startColumnIndex": 9, "endColumnIndex": 10},
                "cell": {"userEnteredFormat": {"wrapStrategy": "CLIP"}},
                "fields": "userEnteredFormat(wrapStrategy)"
            }
        },
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1}, "properties": {"pixelSize": 70}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2}, "properties": {"pixelSize": 180}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 3}, "properties": {"pixelSize": 160}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 3, "endIndex": 4}, "properties": {"pixelSize": 320}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 4, "endIndex": 5}, "properties": {"pixelSize": 140}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 5, "endIndex": 6}, "properties": {"pixelSize": 350}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 6, "endIndex": 7}, "properties": {"pixelSize": 130}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 7, "endIndex": 8}, "properties": {"pixelSize": 130}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 8, "endIndex": 9}, "properties": {"pixelSize": 100}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 9, "endIndex": 10}, "properties": {"pixelSize": 450}, "fields": "pixelSize"}},
        {
            "repeatCell": {
                "range": {"sheetId": 1, "startRowIndex": 3, "endRowIndex": 4, "startColumnIndex": 0, "endColumnIndex": 5},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.106, "green": 0.212, "blue": 0.365},
                        "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True},
                        "horizontalAlignment": "CENTER"
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
            }
        },
        {
            "repeatCell": {
                "range": {"sheetId": 1, "startRowIndex": 4, "endRowIndex": 4 + len(subcat_stats), "startColumnIndex": 2, "endColumnIndex": 5},
                "cell": {"userEnteredFormat": {"numberFormat": {"type": "CURRENCY", "pattern": "#,##0 \"₫\""}, "horizontalAlignment": "RIGHT"}},
                "fields": "userEnteredFormat(numberFormat,horizontalAlignment)"
            }
        }
    ]
    
    batch_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate"
    requests.post(batch_url, headers=headers, json={"requests": format_requests}, timeout=30)
    
    return spreadsheet_id, spreadsheet_url

def main():
    print("=== STARTING DMCL REF SCRAPER & GOOGLE SHEETS SYNC ===")
    data_rows = fetch_dmcl_ref_data()
    
    # Save local backups
    import csv
    with open("dmcl_ref_catalog.json", "w", encoding="utf-8") as f:
        json.dump(data_rows, f, ensure_ascii=False, indent=2)
    with open("dmcl_ref_catalog.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "cat", "sub_cat", "model", "name", "status", "direct_link",
            "mrp_price", "selling_price", "discount_pct", "promotion"
        ])
        writer.writeheader()
        writer.writerows(data_rows)
        
    token = get_google_access_token()
    target_sheet_id = os.environ.get("SPREADSHEET_ID", "1r0oqzTog9jwFhIDl717CUQTsYfAcET_phuDbGyP5tJs")
    
    sheet_id, sheet_url = sync_to_google_sheet(token, data_rows, spreadsheet_id=target_sheet_id)
    
    print("\n================ SUCCESS ================")
    print(f"Total Products Processed: {len(data_rows)}")
    print(f"Target Spreadsheet URL: {sheet_url}")
    print("=========================================")

if __name__ == "__main__":
    main()
