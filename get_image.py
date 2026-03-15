import time
import mss
import numpy as np
import cv2
import pygetwindow as gw
from datetime import datetime

# 引入辨識程式
from analyzer import process_screenshot

def find_real_window(keyword):
    """尋找真正可見的視窗，過濾掉隱藏的「幽靈視窗」"""
    windows = gw.getWindowsWithTitle(keyword)
    for w in windows:
        try:
            # 真正的軟體畫面一定會有寬度和高度。
            # 讀取幽靈視窗的寬高時會報錯，或是寬高為 0，我們藉此過濾掉它們。
            if w.width > 0 and w.height > 0:
                return w
        except Exception:
            continue
    return None

def start_monitoring(window_title_keyword, interval=3):
    print(f"🔍 尋找標題包含「{window_title_keyword}」的視窗...")
    
    target_window = find_real_window(window_title_keyword)
    if not target_window:
        print(f"❌ 找不到有效的「{window_title_keyword}」視窗！請確認軟體已開啟。")
        return
        
    print(f"✅ 成功鎖定視窗: {target_window.title}")
    print("🚀 開始背景監控... (按 Ctrl+C 結束)")

    with mss.mss() as sct:
        try:
            while True:
                start_time = time.time()
                
                # ==== 【新增保護機制：捕捉 1400 錯誤】 ====
                try:
                    # 測試視窗是否依然存在且有效
                    if target_window.isMinimized:
                        print("⚠️ 視窗目前被最小化，等待中...", end="\r")
                        time.sleep(interval)
                        continue
                        
                    # 取得即時範圍
                    monitor_region = {
                        "top": target_window.top,
                        "left": target_window.left,
                        "width": target_window.width,
                        "height": target_window.height
                    }
                except Exception as e:
                    # 如果遇到 1400 錯誤，代表抓到了失效的控制代碼
                    if "1400" in str(e) or "invalid" in str(e).lower():
                        print("\n⚠️ 視窗控制代碼失效，嘗試重新連接視窗...")
                        target_window = find_real_window(window_title_keyword)
                        if not target_window:
                            print("❌ 找不到視窗 (可能已被關閉)，等待 3 秒後重試...", end="\r")
                            time.sleep(3)
                        continue
                    else:
                        raise e  # 如果是其他錯誤就印出來

                # 防呆：確保取得的寬高是正常的才截圖
                if monitor_region["width"] <= 0 or monitor_region["height"] <= 0:
                    time.sleep(1)
                    continue

                # ==========================================
                
                # 1. 局部截圖
                img_bgra = np.array(sct.grab(monitor_region))
                img_bgr = cv2.cvtColor(img_bgra, cv2.COLOR_BGRA2BGR)
                
                # 2. 強制縮放回 1280x720 (避免系統邊框吃掉像素，導致座標錯位)
                img_resized = cv2.resize(img_bgr, (1280, 720))
                
                # 3. 將校準好的圖片送給分析程式
                process_screenshot(img_resized)
                
                # 4. 精準等待
                elapsed = time.time() - start_time
                sleep_time = interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            print("\n🛑 監控已結束。")
        except Exception as e:
            print(f"\n❌ 發生未預期的錯誤: {e}")

if __name__ == '__main__':
    # =========================================================
    # 請把下面這個 "你的軟體名稱" 換成軟體視窗上顯示的文字
    # =========================================================
    TARGET_SOFTWARE_NAME = "League of Legends"
    
    start_monitoring(TARGET_SOFTWARE_NAME, interval=3)