# curriculum.py
DATA = {
    "Toán": {
        "10": {
            "Chương 1. Mệnh đề và tập hợp": [
                "Bài 1. Mệnh đề",
                "Bài 2. Tập hợp và các phép toán trên tập hợp",
                "Bài tập cuối chương 1"
            ],
            "Chương 2. Bất phương trình và hệ bất phương trình bậc nhất hai ẩn": [
                "Bài 3. Bất phương trình bậc nhất hai ẩn",
                "Bài 4. Hệ bất phương trình bậc nhất hai ẩn",
                "Bài tập cuối chương 2"
            ],
            "Chương 3. Hệ thức lượng trong tam giác": [
                "Bài 5. Giá trị lượng giác của một góc từ 0° đến 180°",
                "Bài 6. Hệ thức lượng trong tam giác",
                "Bài tập cuối chương 3"
            ],
            "Chương 4. Vectơ": [
                "Bài 7. Các khái niệm mở đầu",
                "Bài 8. Tổng và hiệu của hai vectơ",
                "Bài 9. Tích của một vectơ với một số",
                "Bài 10. Vectơ trong mặt phẳng toạ độ",
                "Bài 11. Tích vô hướng của hai vectơ",
                "Bài tập cuối chương 4"
            ],
            "Chương 5. Các số đặc trưng của mẫu số liệu không ghép nhóm": [
                "Bài 12. Số gần đúng và sai số",
                "Bài 13. Các số đặc trưng đo xu thế trung tâm",
                "Bài 14. Các số đặc trưng đo độ phân tán",
                "Bài tập cuối chương 5"
            ],
            "Chương 6. Hàm số, đồ thị và ứng dụng": [
                "Bài 15. Hàm số",
                "Bài 16. Hàm số bậc hai",
                "Bài 17. Dấu của tam thức bậc hai",
                "Bài 18. Phương trình quy về phương trình bậc hai",
                "Bài tập cuối chương 6"
            ],
            "Chương 7. Phương pháp toạ độ trong mặt phẳng": [
                "Bài 19. Phương trình đường thẳng",
                "Bài 20. Đường thẳng trong mặt phẳng toạ độ",
                "Bài 21. Đường tròn trong mặt phẳng toạ độ",
                "Bài 22. Ba đường conic",
                "Bài tập cuối chương 7"
            ],
            "Chương 8. Đại số tổ hợp": [
                "Bài 23. Quy tắc đếm",
                "Bài 24. Hoán vị, chỉnh hợp và tổ hợp",
                "Bài 25. Nhị thức Newton",
                "Bài tập cuối chương 8"
            ],
            "Chương 9. Tính xác suất theo định nghĩa cổ điển": [
                "Bài 26. Biến cố và định nghĩa cổ điển của xác suất",
                "Bài 27. Thực hành tính xác suất theo định nghĩa cổ điển",
                "Bài tập cuối chương 9"
            ]
        },
        "11": {
            "Chương 1. Hàm số lượng giác và phương trình lượng giác": [
                "Bài 1. Giá trị lượng giác của góc lượng giác",
                "Bài 2. Công thức lượng giác",
                "Bài 3. Hàm số lượng giác",
                "Bài 4. Phương trình lượng giác cơ bản",
                "Bài tập cuối chương 1"
            ],
            "Chương 2. Dãy số, cấp số cộng và cấp số nhân": [
                "Bài 5. Dãy số",
                "Bài 6. Cấp số cộng",
                "Bài 7. Cấp số nhân",
                "Bài tập cuối chương 2"
            ],
            "Chương 3. Các số đặc trưng đo xu thế trung tâm của mẫu số liệu ghép nhóm": [
                "Bài 8. Mẫu số liệu ghép nhóm",
                "Bài 9. Các số đặc trưng đo xu thế trung tâm",
                "Bài tập cuối chương 3"
            ],
            "Chương 4. Quan hệ song song trong không gian": [
                "Bài 10. Đường thẳng và mặt phẳng trong không gian",
                "Bài 11. Hai đường thẳng song song",
                "Bài 12. Đường thẳng và mặt phẳng song song",
                "Bài 13. Hai mặt phẳng song song",
                "Bài 14. Phép chiếu song song",
                "Bài tập cuối chương 4"
            ],
            "Chương 5. Giới hạn. Hàm số liên tục": [
                "Bài 15. Giới hạn của dãy số",
                "Bài 16. Giới hạn của hàm số",
                "Bài 17. Hàm số liên tục",
                "Bài tập cuối chương 5"
            ],
            "Chương 6. Hàm số mũ và hàm số lôgarit": [
                "Bài 18. Luỹ thừa với số mũ thực",
                "Bài 19. Lôgarit",
                "Bài 20. Hàm số mũ và hàm số lôgarit",
                "Bài 21. Phương trình, bất phương trình mũ và lôgarit",
                "Bài tập cuối chương 6"
            ],
            "Chương 7. Quan hệ vuông góc trong không gian": [
                "Bài 22. Hai đường thẳng vuông góc",
                "Bài 23. Đường thẳng vuông góc với mặt phẳng",
                "Bài 24. Phép chiếu vuông góc. Góc giữa đường thẳng và mặt phẳng",
                "Bài 25. Hai mặt phẳng vuông góc",
                "Bài 26. Khoảng cách",
                "Bài 27. Thể tích",
                "Bài tập cuối chương 7"
            ],
            "Chương 8. Các quy tắc tính xác suất": [
                "Bài 28. Biến cố hợp, biến cố giao, biến cố độc lập",
                "Bài 29. Công thức cộng xác suất",
                "Bài 30. Công thức nhân xác suất cho hai biến cố độc lập",
                "Bài tập cuối chương 8"
            ],
            "Chương 9. Đạo hàm": [
                "Bài 31. Định nghĩa và ý nghĩa của đạo hàm",
                "Bài 32. Các quy tắc tính đạo hàm",
                "Bài 33. Đạo hàm cấp hai",
                "Bài tập cuối chương 9"
            ]
        },
        "12": {
            "Chương 1. Ứng dụng đạo hàm để khảo sát và vẽ đồ thị hàm số": [
                "Bài 1. Tính đơn điệu và cực trị của hàm số",
                "Bài 2. Giá trị lớn nhất và giá trị nhỏ nhất của hàm số",
                "Bài 3. Đường tiệm cận của đồ thị hàm số",
                "Bài 4. Khảo sát sự biến thiên và vẽ đồ thị của hàm số",
                "Bài 5. Ứng dụng đạo hàm để giải quyết một số vấn đề liên quan đến thực tiễn",
                "Bài tập cuối chương 1"
            ],
            "Chương 2. Vectơ và hệ trục toạ độ trong không gian": [
                "Bài 6. Vectơ trong không gian",
                "Bài 7. Hệ trục toạ độ trong không gian",
                "Bài 8. Biểu thức toạ độ của các phép toán vectơ",
                "Bài tập cuối chương 2"
            ],
            "Chương 3. Các số đặc trưng đo mức độ phân tán của mẫu số liệu ghép nhóm": [
                "Bài 9. Khoảng biến thiên và khoảng tứ phân vị",
                "Bài 10. Phương sai và độ lệch chuẩn",
                "Bài tập cuối chương 3"
            ],
            "Chương 4. Nguyên hàm và tích phân": [
                "Bài 11. Nguyên hàm",
                "Bài 12. Tích phân",
                "Bài 13. Ứng dụng hình học của tích phân",
                "Bài tập cuối chương 4"
            ],
            "Chương 5. Phương pháp toạ độ trong không gian": [
                "Bài 14. Phương trình mặt phẳng",
                "Bài 15. Phương trình đường thẳng trong không gian",
                "Bài 16. Công thức tính góc trong không gian",
                "Bài 17. Phương trình mặt cầu",
                "Bài tập cuối chương 5"
            ],
            "Chương 6. Xác suất có điều kiện": [
                "Bài 18. Xác suất có điều kiện",
                "Bài 19. Công thức xác suất toàn phần và công thức Bayes",
                "Bài tập cuối chương 6"
            ]
        }
    },
    "Vật Lí": {
        "10": {
            "Chương 1. Mở đầu": [
                "Bài 1. Làm quen với Vật lí",
                "Bài 2. Các quy tắc an toàn trong phòng thực hành Vật lí",
                "Bài 3. Thực hành tính sai số trong phép đo. Ghi kết quả đo"
            ],
            "Chương 2. Động học": [
                "Bài 4. Độ dịch chuyển và quãng đường đi được",
                "Bài 5. Tốc độ và vận tốc",
                "Bài 6. Thực hành: Đo tốc độ của vật chuyển động",
                "Bài 7. Đồ thị độ dịch chuyển – thời gian",
                "Bài 8. Chuyển động biến đổi. Gia tốc",
                "Bài 9. Chuyển động thẳng biến đổi đều",
                "Bài 10. Sự rơi tự do",
                "Bài 11. Thực hành: Đo gia tốc rơi tự do",
                "Bài 12. Chuyển động ném"
            ],
            "Chương 3. Động lực học": [
                "Bài 13. Tổng hợp và phân tích lực. Cân bằng lực",
                "Bài 14. Định luật 1 Newton",
                "Bài 15. Định luật 2 Newton",
                "Bài 16. Định luật 3 Newton",
                "Bài 17. Trọng lực và lực căng",
                "Bài 18. Lực ma sát",
                "Bài 19. Lực cản và lực nâng",
                "Bài 20. Một số ví dụ về cách giải các bài toán thuộc phần động lực học",
                "Bài 21. Moment lực. Cân bằng của vật rắn",
                "Bài 22. Thực hành: Tổng hợp lực"
            ],
            "Chương 4. Năng lượng, công, công suất": [
                "Bài 23. Năng lượng. Công cơ học",
                "Bài 24. Công suất",
                "Bài 25. Động năng, thế năng",
                "Bài 26. Cơ năng và định luật bảo toàn cơ năng",
                "Bài 27. Hiệu suất"
            ],
            "Chương 5. Động lượng": [
                "Bài 28. Động lượng",
                "Bài 29. Định luật bảo toàn động lượng",
                "Bài 30. Thực hành: Xác định động lượng của vật trước và sau va chạm"
            ],
            "Chương 6. Chuyển động tròn": [
                "Bài 31. Động học của chuyển động tròn đều",
                "Bài 32. Lực hướng tâm và gia tốc hướng tâm"
            ],
            "Chương 7. Biến dạng của vật rắn. Áp suất chất lỏng": [
                "Bài 33. Biến dạng của vật rắn",
                "Bài 34. Khối lượng riêng. Áp suất chất lỏng"
            ]
        },
        "11": {
            "Chương 1. Dao động": [
                "Bài 1. Dao động điều hoà",
                "Bài 2. Mô tả dao động điều hoà",
                "Bài 3. Vận tốc, gia tốc trong dao động điều hoà",
                "Bài 4. Bài tập về dao động điều hoà",
                "Bài 5. Động năng. Thế năng. Sự chuyển hoá giữa động năng và thế năng trong dao động điều hoà",
                "Bài 6. Dao động tắt dần. Dao động cưỡng bức. Hiện tượng cộng hưởng",
                "Bài 7. Bài tập về sự chuyển năng lượng trong dao động điều hoà"
            ],
            "Chương 2. Sóng": [
                "Bài 8. Mô tả sóng",
                "Bài 9. Sóng ngang, sóng dọc, sự truyền năng lượng của sóng cơ",
                "Bài 10. Thực hành: Đo tần số của sóng âm",
                "Bài 11. Sóng điện từ",
                "Bài 12. Giao thoa sóng",
                "Bài 13. Sóng dừng",
                "Bài 14. Bài tập về sóng",
                "Bài 15. Thực hành: Đo tốc độ truyền âm"
            ],
            "Chương 3. Điện trường": [
                "Bài 16. Lực tương tác giữa hai điện tích",
                "Bài 17. Khái niệm điện trường",
                "Bài 18. Điện trường đều",
                "Bài 19. Thế năng điện",
                "Bài 20. Điện thế",
                "Bài 21. Tụ điện"
            ],
            "Chương 4. Dòng điện. Mạch điện": [
                "Bài 22. Cường độ dòng điện",
                "Bài 23. Điện trở. Định luật Ohm",
                "Bài 24. Nguồn điện",
                "Bài 25. Năng lượng điện và công suất điện",
                "Bài 26. Thực hành: Đo suất điện động và điện trở trong của pin điện hoá"
            ]
        },
        "12": {
            "Chương 1. Vật lí nhiệt": [
                "Bài 1. Cấu trúc của chất. Sự chuyển thể",
                "Bài 2. Nội năng. Định luật 1 của nhiệt động lực học",
                "Bài 3. Nhiệt độ. Thang nhiệt độ – nhiệt kế",
                "Bài 4. Nhiệt dung riêng",
                "Bài 5. Nhiệt nóng chảy riêng",
                "Bài 6. Nhiệt hóa hơi riêng",
                "Bài 7. Bài tập về vật lí nhiệt"
            ],
            "Chương 2. Khí lí tưởng": [
                "Bài 8. Mô hình động học phân tử chất khí",
                "Bài 9. Định luật Boyle",
                "Bài 10. Định luật Charles",
                "Bài 11. Phương trình trạng thái của khí lí tưởng",
                "Bài 12. Áp suất khí theo mô hình động học phân tử. Quan hệ giữa động năng phần tử và nhiệt độ",
                "Bài 13. Bài tập về khí lí tưởng"
            ],
            "Chương 3. Từ trường": [
                "Bài 14. Từ trường",
                "Bài 15. Lực từ tác dụng lên dây dẫn mang dòng điện. Cảm ứng từ",
                "Bài 16. Từ thông. Hiện tượng cảm ứng điện từ",
                "Bài 17. Máy phát điện xoay chiều",
                "Bài 18. Ứng dụng hiện tượng cảm ứng điện từ",
                "Bài 19. Điện từ trường. Mô hình sóng điện từ",
                "Bài 20. Bài tập về từ trường"
            ],
            "Chương 4. Vật lí hạt nhân": [
                "Bài 21. Cấu trúc hạt nhân",
                "Bài 22. Phản ứng hạt nhân và năng lượng liên kết",
                "Bài 23. Hiện tượng phóng xạ",
                "Bài 24. Công nghiệp hạt nhân",
                "Bài 25. Bài tập về vật lí hạt nhân"
            ]
        }
    },
    "Hóa Học": {
        "10": {
            "Chương 1. Cấu tạo nguyên tử": [
                "Bài 1. Thành phần của nguyên tử",
                "Bài 2. Nguyên tố hóa học",
                "Bài 3. Cấu trúc lớp vỏ electron nguyên tử",
                "Bài 4. Ôn tập chương 1"
            ],
            "Chương 2. Bảng tuần hoàn các nguyên tố hoá học và định luật tuần hoàn": [
                "Bài 5. Cấu tạo của bảng tuần hoàn các nguyên tố hoá học",
                "Bài 6. Xu hướng biến đổi một số tính chất của nguyên tử các nguyên tố trong một chu kì và trong một nhóm",
                "Bài 7. Xu hướng biến đổi thành phần và một số tính chất của hợp chất trong một chu kì",
                "Bài 8. Định luật tuần hoàn. Ý nghĩa của bảng tuần hoàn các nguyên tố hoá học",
                "Bài 9. Ôn tập chương 2"
            ],
            "Chương 3. Liên kết hoá học": [
                "Bài 10. Quy tắc octet",
                "Bài 11. Liên kết ion",
                "Bài 12. Liên kết cộng hoá trị",
                "Bài 13. Liên kết hydrogen và tương tác van der Waals",
                "Bài 14. Ôn tập chương 3"
            ],
            "Chương 4. Phản ứng oxi hoá – khử": [
                "Bài 15. Phản ứng oxi hoá – khử",
                "Bài 16. Ôn tập chương 4"
            ],
            "Chương 5. Năng lượng hoá học": [
                "Bài 17. Biến thiên enthalpy trong các phản ứng hoá học",
                "Bài 18. Ôn tập chương 5"
            ],
            "Chương 6. Tốc độ phản ứng": [
                "Bài 19. Tốc độ phản ứng",
                "Bài 20. Ôn tập chương 6"
            ],
            "Chương 7. Nguyên tố nhóm halogen": [
                "Bài 21. Nhóm halogen",
                "Bài 22. Hydrogen halide. Muối halide",
                "Bài 23. Ôn tập chương 7"
            ]
        },
        "11": {
            "Chương 1. Cân bằng hoá học": [
                "Bài 1. Khái niệm về cân bằng hoá học",
                "Bài 2. Cân bằng trong dung dịch nước",
                "Bài 3. Ôn tập chương 1"
            ],
            "Chương 2. Nitrogen – Sulfur": [
                "Bài 4. Nitrogen",
                "Bài 5. Ammonia – Muối ammonium",
                "Bài 6. Một số hợp chất của nitrogen với oxygen",
                "Bài 7. Sulfur và sulfur dioxide",
                "Bài 8. Sulfuric acid và muối sulfate",
                "Bài 9. Ôn tập chương 2"
            ],
            "Chương 3. Đại cương về hoá học hữu cơ": [
                "Bài 10. Hợp chất hữu cơ và hoá học hữu cơ",
                "Bài 11. Phương pháp tách biệt và tinh chế hợp chất hữu cơ",
                "Bài 12. Công thức phân tử hợp chất hữu cơ",
                "Bài 13. Cấu tạo hoá học hợp chất hữu cơ",
                "Bài 14. Ôn tập chương 3"
            ],
            "Chương 4. Hydrocarbon": [
                "Bài 15. Alkane",
                "Bài 16. Hydrocarbon không no",
                "Bài 17. Arene (Hydrocarbon thơm)",
                "Bài 18. Ôn tập chương 4"
            ],
            "Chương 5. Dẫn xuất halogen – Alcohol – Phenol": [
                "Bài 19. Dẫn xuất halogen",
                "Bài 20. Alcohol",
                "Bài 21. Phenol",
                "Bài 22. Ôn tập chương 5"
            ],
            "Chương 6. Hợp chất Carbonyl – Carboxylic acid": [
                "Bài 23. Hợp chất carbonyl",
                "Bài 24. Carboxylic acid",
                "Bài 25. Ôn tập chương 6"
            ]
        },
        "12": {
            "Chương 1. Ester – Lipid": [
                "Bài 1. Ester – Lipid",
                "Bài 2. Xà phòng và chất giặt rửa",
                "Bài 3. Ôn tập chương 1"
            ],
            "Chương 2. Carbohydrate": [
                "Bài 4. Giới thiệu về carbohydrate. Glucose và fructose",
                "Bài 5. Saccharose và maltose",
                "Bài 6. Tinh bột và cellulose",
                "Bài 7. Ôn tập chương 2"
            ],
            "Chương 3. Hợp chất chứa Nitrogen": [
                "Bài 8. Amine",
                "Bài 9. Amino acid và peptide",
                "Bài 10. Protein và enzyme",
                "Bài 11. Ôn tập chương 3"
            ],
            "Chương 4. Polymer": [
                "Bài 12. Đại cương về polymer",
                "Bài 13. Vật liệu polymer",
                "Bài 14. Ôn tập chương 4"
            ],
            "Chương 5. Pin điện và điện phân": [
                "Bài 15. Thế điện cực và nguồn điện hóa học",
                "Bài 16. Điện phân",
                "Bài 17. Ôn tập chương 5"
            ],
            "Chương 6. Đại cương về kim loại": [
                "Bài 18. Cấu tạo và liên kết trong tinh thể kim loại",
                "Bài 19. Tính chất vật lí và tính chất hóa học của kim loại",
                "Bài 20. Kim loại trong tự nhiên và phương pháp tách kim loại",
                "Bài 21. Hợp kim",
                "Bài 22. Sự ăn mòn kim loại",
                "Bài 23. Ôn tập chương 6"
            ],
            "Chương 7. Nguyên tố nhóm IA và nhóm IIA": [
                "Bài 24. Nguyên tố nhóm IA",
                "Bài 25. Nguyên tố nhóm IIA",
                "Bài 26. Ôn tập chương 7"
            ],
            "Chương 8. Sơ lược về dãy kim loại chuyển tiếp thứ nhất và phức chất": [
                "Bài 27. Đại cương về kim loại chuyển tiếp dãy thứ nhất",
                "Bài 28. Sơ lược về phức chất",
                "Bài 29. Một số tính chất và ứng dụng của phức chất",
                "Bài 30. Ôn tập chương 8"
            ]
        }
    },
    "Lịch Sử": {
        "11": {
            "Chủ đề 1. Cách mạng tư sản và sự phát triển của chủ nghĩa tư bản": [
                "Bài 1. Một số vấn đề chung về cách mạng tư sản",
                "Bài 2. Sự xác lập và phát triển của chủ nghĩa tư bản"
            ],
            "Chủ đề 2. Chủ nghĩa xã hội từ năm 1917 đến nay": [
                "Bài 3. Sự hình thành Liên bang Cộng hoà xã hội chủ nghĩa Xô viết",
                "Bài 4. Sự phát triển của chủ nghĩa xã hội từ sau Chiến tranh thế giới thứ hai đến nay"
            ],
            "Chủ đề 3. Quá trình giành độc lập dân tộc của các quốc gia Đông Nam Á": [
                "Bài 5. Quá trình xâm lược và cai trị của chủ nghĩa thực dân ở Đông Nam Á",
                "Bài 6. Hành trình đi đến độc lập dân tộc ở Đông Nam Á"
            ],
            "Chủ đề 4. Chiến tranh bảo vệ Tổ quốc và chiến tranh giải phóng dân tộc trong lịch sử Việt Nam (Trước cách mạng tháng Tám năm 1945)": [
                "Bài 7. Chiến tranh bảo vệ Tổ quốc trong lịch sử Việt Nam",
                "Bài 8. Một số cuộc khởi nghĩa và chiến tranh giải phóng trong lịch sử Việt Nam (từ thế kỉ III trước Công nguyên đến cuối thế kỉ XIX)"
            ],
            "Chủ đề 5. Một số cuộc cải cách lớn trong lịch sử Việt Nam (Trước năm 1858)": [
                "Bài 9. Cuộc cải cách của Hồ Quý Ly và triều Hồ",
                "Bài 10. Cuộc cải cách của Lê Thánh Tông (thế kỉ XV)",
                "Bài 11. Cuộc cải cách của Minh Mạng (nửa đầu thế kỉ XIX)"
            ],
            "Chủ đề 6. Lịch sử bảo vệ chủ quyền, các quyền và lợi ích hợp pháp của Việt Nam ở Biển Đông": [
                "Bài 12. Vị trí và tầm quan trọng của Biển Đông",
                "Bài 13. Việt Nam và Biển Đông"
            ]
        }
    },
    "Địa Lí": {
        "11": {
            "Phần Một. Một số vấn đề kinh tế - xã hội thế giới": [
                "Bài 1. Sự khác biệt về trình độ phát triển kinh tế - xã hội của các nhóm nước",
                "Bài 2. Toàn cầu hoá và khu vực hoá kinh tế",
                "Bài 3. Thực hành: Tìm hiểu về cơ hội và thách thức của toàn cầu hoá và khu vực hoá kinh tế",
                "Bài 4. Một số tổ chức quốc tế và khu vực, an ninh toàn cầu",
                "Bài 5. Thực hành: Viết báo cáo về đặc điểm và biểu hiện của nền kinh tế tri thức"
            ],
            "Phần Hai. Địa lí khu vực và quốc gia": [
                "Bài 6. Vị trí địa lí, điều kiện tự nhiên, dân cư và xã hội khu vực Mỹ La-tinh",
                "Bài 7. Kinh tế khu vực Mỹ La-tinh",
                "Bài 8. Thực hành: Viết báo cáo về tình hình phát triển kinh tế - xã hội ở Cộng hoà Liên bang Bra-xin",
                "Bài 9. Liên minh châu Âu (EU) – Một liên kết kinh tế khu vực lớn",
                "Bài 10. Thực hành: Viết báo cáo về sự phát triển công nghiệp của Cộng hoà Liên bang Đức",
                "Bài 11. Vị trí địa lí, điều kiện tự nhiên, dân cư và xã hội khu vực Đông Nam Á",
                "Bài 12. Kinh tế khu vực Đông Nam Á",
                "Bài 13. Hiệp hội các quốc gia Đông Nam Á (ASEAN)",
                "Bài 14. Thực hành: Tìm hiểu hoạt động kinh tế đối ngoại của khu vực Đông Nam Á",
                "Bài 15. Vị trí địa lí, điều kiện tự nhiên, dân cư và xã hội khu vực Tây Nam Á",
                "Bài 16. Kinh tế khu vực Tây Nam Á",
                "Bài 17. Thực hành: Viết báo cáo về vấn đề dầu mỏ của khu vực Tây Nam Á",
                "Bài 18. Vị trí địa lí, điều kiện tự nhiên và dân cư Hoa Kỳ",
                "Bài 19. Kinh tế Hoa Kỳ",
                "Bài 20. Vị trí địa lí, điều kiện tự nhiên, dân cư và xã hội Liên bang Nga",
                "Bài 21. Kinh tế Liên bang Nga",
                "Bài 22. Thực hành: Tìm hiểu về công nghiệp khai thác dầu khí của Liên bang Nga",
                "Bài 23. Vị trí địa lí, điều kiện tự nhiên, dân cư và xã hội Nhật Bản",
                "Bài 24. Kinh tế Nhật Bản",
                "Bài 25. Thực hành: Viết báo cáo về hoạt động kinh tế đối ngoại của Nhật Bản",
                "Bài 26. Vị trí địa lí, điều kiện tự nhiên, dân cư và xã hội Trung Quốc",
                "Bài 27. Kinh tế Trung Quốc",
                "Bài 28. Thực hành: Viết báo cáo về sự thay đổi của kinh tế vùng duyên hải Trung Quốc",
                "Bài 29. Thực hành: Tìm hiểu về kinh tế của Ô-xtrây-li-a",
                "Bài 30. Vị trí địa lí, điều kiện tự nhiên, dân cư và xã hội Cộng hoà Nam Phi",
                "Bài 31. Kinh tế Cộng hoà Nam Phi"
            ]
        }
    },
    "Sinh Học": {
        "10": {
            "Chương 0. Phần mở đầu": [
                "Bài 1. Giới thiệu khái quát môn Sinh học",
                "Bài 2. Phương pháp nghiên cứu và học tập môn Sinh học",
                "Bài 3. Các cấp độ tổ chức của thế giới sống"
            ],
            "Chương 1. Thành phần hoá học của tế bào": [
                "Bài 4. Các nguyên tố hoá học và nước",
                "Bài 5. Các phân tử sinh học",
                "Bài 6. Thực hành: Nhận biết một số phân tử sinh học"
            ],
            "Chương 2. Cấu trúc tế bào": [
                "Bài 7. Tế bào nhân sơ",
                "Bài 8. Tế bào nhân thực",
                "Bài 9. Thực hành: Quan sát tế bào"
            ],
            "Chương 3. Trao đổi chất qua màng và truyền tin tế bào": [
                "Bài 10. Trao đổi chất qua màng tế bào",
                "Bài 11. Thực hành: Thí nghiệm co và phản co nguyên sinh",
                "Bài 12. Truyền tin tế bào"
            ],
            "Chương 4. Chuyển hoá năng lượng trong tế bào": [
                "Bài 13. Khái quát về chuyển hoá vật chất và năng lượng",
                "Bài 14. Phân giải và tổng hợp các chất trong tế bào"
            ],
            "Chương 5. Chu kì tế bào và phân bào": [
                "Bài 16. Chu kì tế bào và nguyên phân",
                "Bài 17. Giảm phân",
                "Bài 18. Thực hành: Làm và quan sát tiêu bản quá trình nguyên phân và giảm phân",
                "Bài 19. Công nghệ tế bào"
            ],
            "Chương 6. Sinh học vi sinh vật": [
                "Bài 20. Sự đa dạng và phương pháp nghiên cứu vi sinh vật",
                "Bài 21. Trao đổi chất, sinh trưởng và sinh sản ở vi sinh vật",
                "Bài 22. Vai trò và ứng dụng của vi sinh vật",
                "Bài 23. Thực hành: Một số phương pháp nghiên cứu vi sinh vật thông dụng, tìm hiểu về các sản phẩm công nghệ vi sinh vật và làm một số sản phẩm lên men từ vi sinh vật"
            ],
            "Chương 7. Virus": [
                "Bài 24. Khái quát về virus",
                "Bài 25. Một số bệnh do virus và các thành tựu nghiên cứu ứng dụng virus",
                "Bài 26. Thực hành: Điều tra một số bệnh do virus và tuyên truyền phòng chống bệnh"
            ]
        },
        "11": {
            "Chương 1. Trao đổi chất và chuyển hoá năng lượng ở sinh vật": [
                "Bài 1. Khái quát về trao đổi chất và chuyển hoá năng lượng",
                "Bài 2. Trao đổi nước và khoáng ở thực vật",
                "Bài 3. Thực hành: Trao đổi nước và khoáng ở thực vật",
                "Bài 4. Quang hợp ở thực vật",
                "Bài 5. Thực hành: Quang hợp ở thực vật",
                "Bài 6. Hô hấp ở thực vật",
                "Bài 7. Thực hành: Hô hấp ở thực vật",
                "Bài 8. Dinh dưỡng và tiêu hoá ở động vật",
                "Bài 9. Hô hấp ở động vật",
                "Bài 10. Tuần hoàn ở động vật",
                "Bài 11. Thực hành: Một số thí nghiệm về tuần hoàn",
                "Bài 12. Miễn dịch ở người và động vật",
                "Bài 13. Bài tiết và cân bằng nội môi"
            ],
            "Chương 2. Cảm ứng ở sinh vật": [
                "Bài 14. Khái quát về cảm ứng ở sinh vật",
                "Bài 15. Cảm ứng ở thực vật",
                "Bài 16. Thực hành: Cảm ứng ở thực vật",
                "Bài 17. Cảm ứng ở động vật",
                "Bài 18. Tập tính ở động vật"
            ],
            "Chương 3. Sinh trưởng và phát triển ở sinh vật": [
                "Bài 19. Khái quát về sinh trưởng và phát triển ở sinh vật",
                "Bài 20. Sinh trưởng và phát triển ở thực vật",
                "Bài 21. Thực hành: Bấm ngọn, tỉa cành, xử lí kích thích, tính tuổi cây",
                "Bài 22. Sinh trưởng và phát triển ở động vật",
                "Bài 23. Thực hành: Quan sát biến thái ở động vật"
            ],
            "Chương 4. Sinh sản ở sinh vật": [
                "Bài 24. Khái quát về sinh sản ở sinh vật",
                "Bài 25. Sinh sản ở thực vật",
                "Bài 26. Thực hành: Nhân giống vô tính và thụ phấn cho cây",
                "Bài 27. Sinh sản ở động vật"
            ],
            "Chương 5. Mối quan hệ giữa các quá trình sinh lí trong cơ thể sinh vật và một số ngành nghề liên quan đến sinh học cơ thể": [
                "Bài 28. Mối quan hệ giữa các quá trình sinh lí trong cơ thể sinh vật",
                "Bài 29. Một số ngành nghề liên quan đến sinh học cơ thể"
            ]
        },
        "12": {
            "Chương 1. Di truyền phân tử": [
                "Bài 1. DNA và cơ chế tái bản DNA",
                "Bài 2. Gene, quá trình truyền đạt thông tin di truyền và hệ gene",
                "Bài 3. Điều hòa biểu hiện của gene",
                "Bài 4. Đột biến gene",
                "Bài 5. Công nghệ di truyền",
                "Bài 6. Thực hành: Tách chiết DNA"
            ],
            "Chương 2. Di truyền nhiễm sắc thể": [
                "Bài 7. Cấu trúc và chức năng của NST",
                "Bài 8. Học thuyết di truyền của Menđel",
                "Bài 9. Mở rộng học thuyết Menđel",
                "Bài 10. Di truyền giới tính và di truyền liên kết với giới tính",
                "Bài 11. Liên kết gene và hoán vị gene",
                "Bài 12. Đột biến NST",
                "Bài 13. Di truyền học người và di truyền y học",
                "Bài 14. Thực hành: Quan sát một số dạng đột biến NST"
            ],
            "Chương 3. Mở rộng học thuyết di truyền nhiễm sắc thể": [
                "Bài 15. Di truyền gene ngoài nhân",
                "Bài 16. Tương tác giữa kiểu gene với môi trường và thành tựu chọn giống",
                "Bài 17. Thực hành: Thí nghiệm về thường biến ở cây trồng"
            ],
            "Chương 4. Di truyền quần thể": [
                "Bài 18. Di truyền quần thể"
            ],
            "Chương 5. Bằng chứng và các học thuyết tiến hóa": [
                "Bài 19. Các bằng chứng tiến hóa",
                "Bài 20. Học thuyết Darwin về chọn lọc tự nhiên và hình thành loài",
                "Bài 21. Học thuyết tiến hóa tổng hợp hiện đại",
                "Bài 22. Tiến hóa lớn và quá trình phát sinh chủng loại"
            ],
            "Chương 6. Môi trường và sinh thái học quần thể": [
                "Bài 23. Môi trường và các nhân tố sinh thái",
                "Bài 24. Sinh thái học quần thể",
                "Bài 25. Thực hành: Xác định khu vực phân bố, kiểu phân bố cá thể và ước tính kích thước mật độ của quần thể thực vật hoặc động vật ít di chuyển"
            ],
            "Chương 7. Sinh thái học quần xã": [
                "Bài 26. Quần xã sinh vật",
                "Bài 27. Thực hành: Tìm hiểu một số đặc trưng cơ bản của quần xã trong tự nhiên",
                "Bài 28. Hệ sinh thái",
                "Bài 29. Trao đổi chất và chuyển hóa năng lượng trong hệ sinh thái",
                "Bài 30. Diễn thế",
                "Bài 31. Sinh quyển, khu sinh học và chu trình sinh - địa - hóa",
                "Bài 32. Thực hành: Thiết kế một hệ sinh thái nhân tạo"
            ],
            "Chương 8. Sinh thái học phục hồi, bảo tồn và phát triển bền vững": [
                "Bài 33. Sinh thái học phục hồi và bảo tồn đa dạng",
                "Bài 34. Phát triển bền vững",
                "Bài 35. Dự án: Tìm hiểu thực trạng bảo tồn sinh thái ở địa phương và đề xuất giải pháp bảo tồn"
            ]
        }
    },
    "Giáo Dục Kinh Tế và Pháp Luật": {
        "11": {
            "Chủ đề 1. Cạnh tranh, cung – cầu trong nền kinh tế thị trường": [
                "Bài 1. Cạnh tranh trong nền kinh tế thị trường",
                "Bài 2. Cung – cầu trong nền kinh tế thị trường"
            ],
            "Chủ đề 2. Lạm phát, thất nghiệp": [
                "Bài 3. Lạm phát",
                "Bài 4. Thất nghiệp"
            ],
            "Chủ đề 3. Thị trường lao động và việc làm": [
                "Bài 5. Thị trường lao động và việc làm"
            ],
            "Chủ đề 4. Ý tưởng, cơ hội kinh doanh và các năng lực cần thiết của người kinh doanh": [
                "Bài 6. Ý tưởng, cơ hội kinh doanh và các năng lực cần thiết của người kinh doanh"
            ],
            "Chủ đề 5. Đạo đức kinh doanh": [
                "Bài 7. Đạo đức kinh doanh"
            ],
            "Chủ đề 6. Văn hoá tiêu dùng": [
                "Bài 8. Văn hoá tiêu dùng"
            ],
            "Chủ đề 7. Quyền bình đẳng của công dân trước pháp luật": [
                "Bài 9. Quyền bình đẳng của công dân trước pháp luật",
                "Bài 10. Bình đẳng giới trong các lĩnh vực",
                "Bài 11. Quyền bình đẳng giữa các dân tộc",
                "Bài 12. Quyền bình đẳng giữa các tôn giáo"
            ],
            "Chủ đề 8. Một số quyền dân chủ cơ bản của công dân": [
                "Bài 13. Quyền và nghĩa vụ của công dân trong tham gia quản lí nhà nước và xã hội",
                "Bài 14. Quyền và nghĩa vụ của công dân về bầu cử và ứng cử",
                "Bài 15. Quyền và nghĩa vụ của công dân về khiếu nại, tố cáo",
                "Bài 16. Quyền và nghĩa vụ của công dân về bảo vệ Tổ quốc"
            ],
            "Chủ đề 9. Một số quyền tự do cơ bản của công dân": [
                "Bài 17. Quyền bất khả xâm phạm về thân thể và quyền được pháp luật bảo hộ về tính mạng, sức khoẻ, danh dự, nhân phẩm của công dân",
                "Bài 18. Quyền bất khả xâm phạm về chỗ ở của công dân",
                "Bài 19. Quyền được bảo đảm an toàn và bí mật thư tín, điện thoại, điện tín của công dân",
                "Bài 20. Quyền và nghĩa vụ của công dân về tự do ngôn luận, báo chí và tiếp cận thông tin",
                "Bài 21. Quyền và nghĩa vụ của công dân về tự do tín ngưỡng và tôn giáo"
            ]
        }
    },
    "Tiếng Anh": {
        "11": {
            "Unit 1. A long and healthy life": [
                "Getting Started",
                "Language",
                "Reading",
                "Speaking",
                "Listening",
                "Writing",
                "Communication and Culture / CLIL",
                "Looking Back",
                "Project"
            ],
            "Unit 2. The generation gap": [
                "Getting Started",
                "Language",
                "Reading",
                "Speaking",
                "Listening",
                "Writing",
                "Communication and Culture / CLIL",
                "Looking Back",
                "Project"
            ],
            "Unit 3. Cities of the future": [
                "Getting Started",
                "Language",
                "Reading",
                "Speaking",
                "Listening",
                "Writing",
                "Communication and Culture / CLIL",
                "Looking Back",
                "Project"
            ],
            "Unit 4. ASEAN and Viet Nam": [
                "Getting Started",
                "Language",
                "Reading",
                "Speaking",
                "Listening",
                "Writing",
                "Communication and Culture / CLIL",
                "Looking Back",
                "Project"
            ],
            "Unit 5. Global warming": [
                "Getting Started",
                "Language",
                "Reading",
                "Speaking",
                "Listening",
                "Writing",
                "Communication and Culture / CLIL",
                "Looking Back",
                "Project"
            ],
            "Unit 6. Preserving our heritage": [
                "Getting Started",
                "Language",
                "Reading",
                "Speaking",
                "Listening",
                "Writing",
                "Communication and Culture / CLIL",
                "Looking Back",
                "Project"
            ],
            "Unit 7. Education options for school-leavers": [
                "Getting Started",
                "Language",
                "Reading",
                "Speaking",
                "Listening",
                "Writing",
                "Communication and Culture / CLIL",
                "Looking Back",
                "Project"
            ],
            "Unit 8. Becoming independent": [
                "Getting Started",
                "Language",
                "Reading",
                "Speaking",
                "Listening",
                "Writing",
                "Communication and Culture / CLIL",
                "Looking Back",
                "Project"
            ],
            "Unit 9. Social issues": [
                "Getting Started",
                "Language",
                "Reading",
                "Speaking",
                "Listening",
                "Writing",
                "Communication and Culture / CLIL",
                "Looking Back",
                "Project"
            ],
            "Unit 10. The ecosystem": [
                "Getting Started",
                "Language",
                "Reading",
                "Speaking",
                "Listening",
                "Writing",
                "Communication and Culture / CLIL",
                "Looking Back",
                "Project"
            ],
            "Reviews": [
                "Review 1",
                "Review 2",
                "Review 3",
                "Review 4"
            ]
        }
    }
}
