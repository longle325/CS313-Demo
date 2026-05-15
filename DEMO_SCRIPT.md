# Kịch Bản Demo Web — 3 Phút

## Thông Điệp Chính

Demo này không chỉ là một model cho ra điểm số. Đây là một workflow dự đoán đa dạng sinh học theo không gian-thời gian: xem bản đồ Việt Nam theo grid cell, chọn một grid năm 2024, nhập giả định môi trường cho 2025, rồi chạy prediction và audit các feature model đang dùng.

## Chuẩn Bị

- Mở `http://127.0.0.1:5173/`.
- Để `Year = 2024` khi demo inference.
- Để `Min observed records = 0`.
- Giữ model mặc định `XGBoost logistic`.
- Nếu vừa sửa code backend, restart FastAPI trước khi demo.

## 0:00–0:25 — Mở Đầu

**Thao tác:** Chỉ vào bản đồ Việt Nam.

**Nói:**
> Thay vì chỉ báo cáo test score trong notebook, demo này cho thấy biodiversity richness index trực tiếp trên bản đồ Việt Nam. Mỗi điểm là một grid cell, và màu thể hiện mức richness index trên thang 0 đến 1.

**Nhấn mạnh:** Đây là bài toán spatial prediction, không chỉ tabular regression.

## 0:25–0:50 — Giải Thích Bản Đồ

**Thao tác:** Chỉ vào legend và đổi nhanh một hai năm nếu muốn.

**Nói:**
> Màu xanh là richness index cao hơn, vàng/cam là trung bình, đỏ là thấp hơn. Điểm này là chỉ số tương đối đã điều chỉnh theo observation effort, không phải số loài tuyệt đối ngoài tự nhiên.

**Nếu nói về timeline:**
> Các năm 2009–2024 là lịch sử quan sát. Khi chọn grid ở năm 2024, hệ thống dùng trạng thái mới nhất này để project sang 2025.

## 0:50–1:20 — Chọn Grid

**Thao tác:** Click một marker xanh hoặc vàng-xanh rõ.

**Nói:**
> Sau khi chọn grid, panel bên phải cho biết Grid ID, tọa độ, richness index, số species/observations và forest context. Đây là thông tin giúp người xem thấy model đang dựa trên tín hiệu sinh thái và lịch sử quan sát, không phải nhập bừa.

**Chỉ màn hình:** `Grid information`.

## 1:20–1:55 — Chạy Prediction

**Thao tác:**
1. Chỉ vào panel `Prediction`.
2. Giữ model `XGBoost logistic`.
3. Chỉ vào `Input 2025`: `Forest cover (%)`, `Forest loss (ha)`.
4. Click `Run prediction`.
5. Chỉ vào `2025 prediction result`.

**Nói:**
> Flow inference là: chọn grid năm 2024, chọn model, nhập giả định môi trường cho năm 2025, rồi chạy prediction. Output là predicted biodiversity richness index trên cùng thang 0 đến 1. Nếu mình chỉnh forest cover hoặc forest loss rồi chạy lại, score sẽ cập nhật theo giả định mới.

## 1:55–2:35 — Feature Audit Nếu Thầy Hỏi Sâu

**Thao tác:** Chỉ vào `Feature audit`.

**Nói ngắn gọn:**
> Bảng này là audit của input model. `Value` là giá trị feature của grid đang chọn, `Median` là median trong training data, còn `Δ score` là local sensitivity: nếu riêng feature đó được đưa về median training, prediction sẽ thay đổi khoảng bao nhiêu điểm trên thang 0–1.

**Ví dụ dễ nói:**
> Nếu `Prior records for cell` có `Value = 4`, `Median = 2`, `Δ score = +0.014`, nghĩa là với giá trị hiện tại của feature này, prediction cao hơn khoảng 0.014 điểm so với khi thay riêng feature đó bằng median training. Đây là cách đọc sensitivity của model, không phải phần trăm tăng biodiversity.

**Nếu thầy hỏi vì sao có feature dấu ngược trực giác:**
> Với tree model, `Δ score` là local sensitivity có interaction với các feature khác, nên không đọc như quan hệ nhân quả đơn biến. Nếu muốn kiểm tra tác động quản lý rõ hơn, em dùng phần input forest cover/loss rồi chạy lại prediction như một scenario có kiểm soát.

**Câu quan trọng để tránh bị bắt bẻ:**
> `Year` không được dùng như một model feature trong audit. Năm chỉ dùng để chọn context 2024 và projection target 2025. Nhóm tránh đưa raw year vào model vì nó dễ biến thành time-index shortcut khi forecast ra tương lai.

## 2:35–2:55 — Scenario Mini Demo

**Thao tác:**
1. Giảm `Forest cover (%)` hoặc tăng `Forest loss (ha)`.
2. Click `Run prediction`.
3. So sánh score mới với score trước đó bằng lời nói.

**Nói:**
> Đây là phần decision-support: mình có thể hỏi nếu forest cover giảm hoặc forest loss tăng thì predicted richness index của grid này thay đổi thế nào. Demo không chỉ đưa ra prediction, mà cho phép thử nhanh một giả định môi trường.

## 2:55–3:10 — Kết Luận

**Nói:**
> Tóm lại, project kết nối dữ liệu biodiversity, forest context, model prediction và feature audit trên bản đồ Việt Nam. Vì vậy sản phẩm cuối không chỉ là notebook model, mà là một spatiotemporal biodiversity forecasting demo.

## Không Nên Nói Trừ Khi Bị Hỏi

- Không nói model dự đoán chính xác số loài tuyệt đối.
- Không nói `Δ score` là causal effect.
- Không giải thích từng feature quá lâu.
- Không xin lỗi vì rainfall missing.
- Không mở notebook/code trong demo live nếu không bị yêu cầu.

## Câu Trả Lời Dự Phòng

### Vì sao không có rainfall trong UI?

> Weather features đã được kiểm tra trong ablation, nhưng không cải thiện rõ kết quả holdout. Demo tập trung vào nhóm feature chắc hơn: historical biodiversity, observation history và forest context.

### High/Medium/Low có phải chuẩn sinh học tuyệt đối không?

> Không. Đây là nhãn diễn giải dựa trên percentile của prediction trong dataset, không phải chuẩn sinh học tuyệt đối.

### Model có dự đoán số loài tuyệt đối không?

> Không. Model dự đoán relative normalized richness index trên thang 0–1, đã điều chỉnh theo observation effort.

### Vì sao không dùng raw year làm feature?

> Vì raw year rất dễ trở thành shortcut theo thời gian, đặc biệt khi project sang 2025 là ngoài khoảng training. Nhóm dùng lag/history features thay cho raw year để mô hình dựa vào lịch sử biodiversity thật của grid.

### Vì sao dropdown có nhiều model?

> Dropdown hiển thị các model chính trong leaderboard để demo có thể so sánh model family. Baseline đơn giản không đưa vào vì chỉ dùng để sanity-check trong notebook, không phải model triển khai.
