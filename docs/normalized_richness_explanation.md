# Giải thích output `normalized_richness_01`

## Output hiện tại biểu thị gì?

Trong pipeline hiện tại, output chính của mô hình là:

```text
normalized_richness_01
```

Đây là một **chỉ số tương đối từ 0 đến 1** dùng để biểu diễn mức độ đa dạng sinh học theo từng **ô lưới không gian (`grid_id`) và từng năm (`year`)**.

Nó không phải là số loài tuyệt đối, cũng không có đơn vị vật lý như `loài/km²`. Có thể hiểu nó là:

> Chỉ số richness đã điều chỉnh theo sampling effort, sau đó chuẩn hóa về khoảng 0–1.

## Công thức

Pipeline hiện tại tính chỉ số này theo hai bước:

```text
effort_adjusted_richness = n_species / log1p(n_observations)
```

Sau đó chuẩn hóa:

```text
normalized_richness_01 =
  min(effort_adjusted_richness, p99_cap) / p99_cap
```

Trong dataset 2009–2024 hiện tại:

```text
p99_cap = 26.897536438578083
```

`p99_cap` là ngưỡng percentile 99 được tính từ các năm train trước năm 2024. Việc dùng percentile 99 giúp tránh để một vài điểm cực lớn làm méo toàn bộ thang đo.

## Ý nghĩa các biến

- `n_species`: số loài ghi nhận được trong một ô lưới ở một năm.
- `n_observations`: số bản ghi GBIF trong một ô lưới ở một năm.
- `log1p(n_observations)`: cách giảm ảnh hưởng của số lượng quan sát quá lớn.
- `effort_adjusted_richness`: số loài đã được điều chỉnh theo sampling effort.
- `normalized_richness_01`: phiên bản chuẩn hóa về khoảng 0–1 để mô hình học và dự đoán ổn định hơn.

## Cách diễn giải giá trị output

Giá trị `normalized_richness_01` càng cao thì ô lưới đó được xem là có mức đa dạng sinh học quan sát được càng cao, sau khi đã điều chỉnh phần nào theo số lượng quan sát.

Ví dụ:

- `0.05`: richness quan sát được thấp so với toàn bộ dataset.
- `0.50`: richness đã điều chỉnh đạt khoảng 50% so với ngưỡng top 1% của dữ liệu train.
- `1.00`: richness rất cao, hoặc đã vượt ngưỡng percentile 99 và bị cap về 1.

Vì vậy, `0.50` không có nghĩa là “50% đa dạng sinh học thật của khu vực”. Nó chỉ có nghĩa là điểm đó đạt khoảng 50% trên thang đo tương đối của dataset.

## Đơn vị

Chỉ số này là **unitless** — không có đơn vị.

Cách gọi phù hợp trong báo cáo:

> Normalized effort-adjusted species richness index, scaled from 0 to 1.

Hoặc tiếng Việt:

> Chỉ số richness loài đã điều chỉnh theo sampling effort, được chuẩn hóa về khoảng 0–1.

## Vì sao cần điều chỉnh theo `n_observations`?

Dữ liệu GBIF không phải dữ liệu khảo sát đồng đều. Những nơi dễ tiếp cận, đông người, gần thành phố hoặc có nhiều nhà quan sát thường có nhiều bản ghi hơn. Nếu chỉ dùng `n_species`, mô hình có thể học rằng nơi nào có nhiều người quan sát hơn thì nơi đó “đa dạng hơn”, dù thực tế có thể chỉ là bias thu thập dữ liệu.

Do đó pipeline dùng:

```text
n_species / log1p(n_observations)
```

Cách này vẫn giữ tín hiệu số loài, nhưng làm giảm tác động của các ô có quá nhiều observation.

## Hạn chế cần ghi rõ

Chỉ số này nên được hiểu là **observed biodiversity index**, không phải đa dạng sinh học tuyệt đối ngoài tự nhiên.

Một số nguồn bias vẫn còn:

- GBIF phụ thuộc vào nơi có người quan sát và upload dữ liệu.
- Một số nhóm loài dễ quan sát hơn, ví dụ chim, cây lớn, côn trùng phổ biến.
- Các khu vực khó tiếp cận có thể bị thiếu dữ liệu.
- Một số năm hoặc ô lưới có rất ít observation, khiến richness không ổn định.
- Việc chia cho `log1p(n_observations)` chỉ giảm bias sampling effort, không loại bỏ hoàn toàn bias.

## Khuyến nghị khi trình bày kết quả

Nên mô tả output là:

> Mô hình dự đoán chỉ số richness loài đã điều chỉnh theo sampling effort, chuẩn hóa trong khoảng 0–1, cho từng ô lưới theo từng năm tại Việt Nam.

Không nên mô tả là:

> Mô hình dự đoán chính xác mức đa dạng sinh học thật ngoài tự nhiên.

Nếu cần diễn giải trên bản đồ:

- Màu nhạt: richness đã điều chỉnh thấp.
- Màu đậm: richness đã điều chỉnh cao.
- Giá trị gần 1: điểm rất giàu loài theo dữ liệu GBIF đã xử lý.
- Giá trị gần 0: điểm có richness thấp hoặc dữ liệu quan sát hạn chế.

