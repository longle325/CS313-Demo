# Kịch Bản Demo Web — Flow Thuyết Trình 3 Phút

## Thông Điệp Chính

Demo này không chỉ là “một model cho ra điểm số”. Đây là một **hệ thống dự đoán đa dạng sinh học theo không gian-thời gian cho Việt Nam**: bản đồ một thang đo 0–1 → chọn grid → chọn model từ leaderboard → xem dự đoán → giải thích model → mô phỏng kịch bản môi trường.

## Chuẩn Bị Trước Khi Demo

- Mở `http://127.0.0.1:5173/`.
- Để `Year = 2024` khi bắt đầu, sau đó chuyển sang `2025` để demo projection.
- Map chỉ có một layer: `Biodiversity richness index · fixed 0–1 scale`.
- Để `Min observations = 0`.
- Trong panel inference, để model mặc định là `XGBoost logistic (validation-selected final)`.
- Không nói về rainfall nếu không bị hỏi.

## 0:00–0:20 — Mở Đầu Gây Chú Ý

**Thao tác:** Chỉ vào bản đồ Việt Nam.

**Nói:**
> Thay vì chỉ báo cáo một con số test score, demo cuối kỳ của nhóm cho thấy biodiversity richness index trên bản đồ Việt Nam theo cùng một thang 0 đến 1 qua các năm.

**Ý chính:** Định vị project là bài toán spatial prediction, không chỉ là tabular model.

## 0:20–0:45 — Giải Thích Bản Đồ

**Thao tác:** Chỉ vào legend.

**Nói:**
> Mỗi điểm trên bản đồ là một grid cell. Màu xanh nghĩa là richness index cao hơn, màu vàng là trung bình, và màu đỏ là thấp hơn. Quan trọng là scale màu cố định từ 0 đến 1 cho mọi năm, nên màu giữa các năm có thể so sánh trực tiếp.

Nói thêm:
> Điểm số này là chỉ số tương đối từ 0 đến 1, đã được điều chỉnh theo observation effort. Nó không phải số loài tuyệt đối ngoài tự nhiên.

**Thao tác phụ nếu muốn gây ấn tượng:** đổi `Year` sang `2025`.

**Nói:**
> Với 2025, đây là projection từ trạng thái grid mới nhất, không phải ground truth. Em sẽ gọi rõ là projection để tránh hiểu nhầm.

## 0:45–1:20 — Chọn Một Grid Cụ Thể

**Thao tác:** Click trực tiếp một marker màu xanh hoặc vàng-xanh rõ trên bản đồ.

**Nói:**
> Khi chọn một grid, panel bên phải hiển thị Grid ID, tọa độ, forest context và evidence quan sát được. Sau đó em mới chọn model và chạy inference cho đúng grid-year đang chọn.

**Chỉ vào màn hình:** `Grid information` và `Model inference`.

**Lưu ý:** Đừng giải thích quá dài từng feature. Chỉ cần nhấn mạnh input có ý nghĩa sinh thái.

## 1:20–1:50 — Chạy Inference Và Kết Quả Dự Đoán

**Thao tác:**
1. Trong dropdown model, giữ `XGBoost logistic (validation-selected final)` hoặc chọn một model khác trong leaderboard.
2. Click nút `Run inference for 2024` hoặc năm đang chọn.
3. Chỉ vào `Prediction result`.

**Nói:**
> Flow inference ở đây là rõ ràng: chọn grid, chọn trained model trong leaderboard, rồi chạy prediction cho năm đang chọn. Với grid này, model dự đoán normalized richness score là giá trị này trên thang 0 đến 1. Nhãn High/Medium/Low được chia theo percentile của prediction trong dataset, không phải một ngưỡng sinh học tuyệt đối.

**Cụm nên nhấn mạnh:** “data-driven interpretation label”.

## 1:50–2:20 — Giải Thích Vì Sao Model Dự Đoán Như Vậy

**Thao tác:** Chỉ vào `Top model factors`.

**Nói:**
> Phần này trả lời câu hỏi: vì sao model đưa ra dự đoán đó? Positive nghĩa là feature đẩy prediction lên, Negative nghĩa là kéo prediction xuống. Con số phần trăm ở đây là `impact share`: tức là trong các yếu tố top đang hiển thị, yếu tố này chiếm bao nhiêu phần ảnh hưởng tương đối. Nó không có nghĩa là biodiversity tăng 30%, cũng không có nghĩa score tăng thêm 0.30.

**Câu giải thích ngắn về `% impact share`:**
> Ví dụ `Previous-year richness · Positive · 45% impact share` nghĩa là trong nhóm yếu tố quan trọng nhất của grid này, historical richness là nguồn ảnh hưởng lớn nhất và đang kéo prediction lên. Còn `Forest loss · Negative · 20% impact share` nghĩa là mất rừng chiếm khoảng 20% ảnh hưởng tương đối trong các top factors và đang kéo prediction xuống. Các phần trăm này cộng lại theo nhóm top factors để giúp mình so sánh yếu tố nào quan trọng hơn, không phải đơn vị sinh học tuyệt đối.

**Ví dụ diễn giải nếu thầy hỏi “nó có nghĩa là gì?”:**
> Ví dụ nếu top factors hiện `Previous-year richness` là Positive và `Forest cover` là Positive, em sẽ nói: grid này được dự đoán cao hơn vì năm trước đã có tín hiệu đa dạng sinh học tương đối tốt và habitat rừng vẫn còn hỗ trợ. Nếu `Forest loss` hoặc `Years since seen` là Negative, nghĩa là disturbance hoặc tín hiệu gần đây yếu hơn đang kéo prediction xuống. Nói ngắn gọn: model không đoán bừa một con số, mà đang cân bằng giữa lịch sử biodiversity của grid và áp lực môi trường hiện tại.

**Cách đọc nhanh trên màn hình:**
- `Previous-year richness` Positive: khu vực có biodiversity signal ổn định từ lịch sử gần.
- `Forest cover` Positive: habitat còn tốt nên richness index được đẩy lên.
- `Forest loss` Negative: mất rừng là pressure, kéo score xuống.
- `% impact share`: tỷ trọng ảnh hưởng tương đối trong các top factors, không phải phần trăm tăng/giảm biodiversity.
- `Years since seen` Negative: tín hiệu biodiversity gần đây yếu hơn hoặc thiếu quan sát mới ở grid đó.
- `Prior records` Positive: grid có lịch sử dữ liệu đủ tốt, giúp model tự tin hơn về pattern của khu vực.

Nói thêm:
> Điểm quan trọng là model dựa nhiều vào historical biodiversity và forest context, chứ không dùng current-year species count để gian lận.

## 2:20–2:55 — Mô Phỏng Kịch Bản

**Thao tác:**
1. Giữ grid vừa chọn, hoặc click một marker khác nếu muốn so sánh khu vực.
2. Click `Run inference for <năm đang chọn>` nếu vừa đổi grid hoặc đổi năm.
3. Scroll tới `Scenario simulation`.
4. Click `Apply degradation scenario`.
5. Click `Run scenario prediction`.

**Nói trước khi bấm run:**
> Bây giờ em mô phỏng một câu hỏi kiểu environmental management: nếu forest cover giảm và forest loss tăng, predicted biodiversity index sẽ thay đổi như thế nào?

**Nói sau khi kết quả hiện ra:**
> Demo so sánh điểm ban đầu với điểm sau kịch bản. Ở đây score giảm, cho thấy forest degradation có thể làm giảm predicted biodiversity richness ở grid này.

**Ý chính:** Đây là decision-support tool, không chỉ là prediction dashboard.

## 2:55–3:10 — Kết Luận

**Nói:**
> Tóm lại, hệ thống cuối cùng kết nối prediction, explanation và scenario analysis trực tiếp trên bản đồ Việt Nam. Vì vậy project này không chỉ là một tabular model, mà là một spatiotemporal biodiversity forecasting demo.

## Nếu Còn Thời Gian

**Thao tác:** Click một marker màu đỏ/đỏ-cam trên bản đồ.

**Nói:**
> Với grid có prediction thấp hơn, workflow vẫn giống như vậy: xem grid information, prediction, explanation và scenario. Điều này cho thấy hệ thống hoạt động nhất quán trên nhiều khu vực.

## Không Nên Nói Trừ Khi Bị Hỏi

- Không nói “model dự đoán chính xác số loài”.
- Không giải thích từng feature quá lâu.
- Không xin lỗi vì rainfall missing.
- Không mở notebook/code trong demo live nếu không bị yêu cầu.

## Câu Trả Lời Dự Phòng

### Vì sao panel không hiện rainfall?

> Weather features đã được test trong ablation, nhưng không cải thiện kết quả holdout 2024. Nhóm không muốn tự điền rainfall thiếu một cách giả tạo, nên demo tập trung vào các signal chắc chắn hơn của final model: forest context và historical biodiversity.

### High/Medium/Low có phải chuẩn sinh học tuyệt đối không?

> Không. Đây là nhãn diễn giải dựa trên percentile của prediction trong dataset, không phải chuẩn sinh học tuyệt đối.

### Model có dự đoán số loài tuyệt đối không?

> Không. Model dự đoán một relative normalized richness index, đã điều chỉnh theo observation effort.

### Vì sao dùng XGBoost?

> Dữ liệu của bài toán là sparse tabular spatiotemporal data, nên tree-based ensemble models phù hợp. Final model được chọn dựa trên feature ablation và model-family comparison, không phải chỉ thử một model duy nhất.

### Vì sao dropdown có nhiều model?

> Dropdown đang hiển thị các model triển khai trong final leaderboard, trừ baseline đơn giản vì baseline chỉ dùng để sanity-check chứ không phải model demo. Model mặc định là XGBoost logistic vì nó được chọn bằng validation year 2023 trước khi test 2024.

### Vì sao có 2025?

> 2025 là projection scenario, không phải ground truth. Nó dùng trạng thái grid mới nhất và giả định persistence để minh họa hệ thống có thể mở rộng thành decision-support tool.
