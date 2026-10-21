import { createContext, useContext, useEffect, useState } from "react";

const en = {
  dashboard: "Main Dashboard", inventory: "Inventory", menuStock: "Menu Stock", pos: "POS Cashier", riderStock: "Rider Stock", deposit: "Deposit",
  invoice: "Invoice", riderDash: "Rider Dashboard", handover: "Cash Transfer / Handover", finance: "Financial Report", salary: "Rider Rank Target", profile: "Profile",
  settings: "Settings", reports: "Reports", purchaseOrders: "Purchase Orders", broadcast: "Broadcast", paymentAccounts: "Payment Accounts", more: "More", logout: "Logout", main: "Main", stock: "Stock", today: "Today", yesterday: "Yesterday", week: "This Week", month: "This Month",
  prevmonth: "Previous Month", prevweek: "Previous Week", custom: "Custom", cupsSold: "Cups Sold", cashRevenue: "Cash Revenue", qrisRevenue: "QRIS Revenue", expenses: "Expenses",
  save: "Save", cancel: "Cancel", sendWA: "Send to WhatsApp", download: "Download", login: "Sign In", username: "Username or Email", password: "Password",
  remember: "Remember me on this device", pin: "PIN", enterPin: "Enter your PIN to open the cashier", selectRider: "Select Rider", allRiders: "All Riders",
  date: "Date", time: "Time", total: "Total", remaining: "Remaining", price: "Price", qty: "Qty", saveRider: "Save Rider Data", welcome: "Welcome back",
  darkMode: "Dark Mode", lightMode: "Light Mode", language: "Language", notifications: "Notifications", gps: "GPS (Rider only)", whileUsing: "Allow While Using the App",
  lowStock: "Low stock", checkIn: "Check In", checkOut: "Check Out", endDay: "End Today's Sales", history: "Sales History", customer: "Customer",
  cashReceived: "Cash Received", change: "Change", checkout: "Pay", receipt: "Receipt", newDeposit: "New Deposit", incentive: "Incentive",
  attendance: "Days Attended", gross: "Gross Revenue", placement: "Placement", joined: "Joined", nextTier: "Next Tier", bestSelling: "Best-Selling Products",
  activeRiders: "Riders on Duty", income: "Money In", outgo: "Money Out", balance: "Balance", addExpense: "Add Expense", noData: "No data for this period", category: "Category",
  rider: "Rider", pic: "PIC", menu: "Menu", wastage: "Wastage", sold: "Sold", diff: "Diff", minus: "Minus", cash: "Cash", qris: "QRIS", totalIncome: "Total Income",
  totalSold: "Total Sold", newDebt: "New Debt", initialDebt: "Initial Debt", remainingDebt: "Remaining Debt", debtPayment: "Debt Payment", netCash: "Net Cash Deposit",
  commission: "Rider Commission", saveDb: "Save to Database", photoEvidence: "Photo Evidence", photoRequired: "Photo evidence is required", takePhoto: "Take Photo",
  stockReport: "Stock Report", orderItems: "Order Items", material: "Material", type: "Type", note: "Note", status: "Status", recipes: "Recipes", production: "Production",
  bundling: "Bundling", cups: "cups", paid: "PAID", unpaid: "UNPAID", downPayment: "Down Payment", remainingPayment: "Remaining Payment", createInvoice: "Create Invoice",
  dailyAllowance: "Daily Attendance", withdraw: "Withdraw", withdrawals: "Withdrawal History", method: "Method", bank: "Bank", amount: "Amount", available: "Available",
  totalCups: "Total Cups Sold", dailySales: "Daily Sales", exportPdf: "Export PDF", print: "Print", excel: "Excel", expectedCash: "Cash That Should Be Received",
  receivedCash: "Total Cash Received", difference: "Difference", addLine: "Add line", giver: "Giving PIC (Bar Team)", receiver: "Receiving PIC", handoverDate: "Handover Date",
  period: "Period", details: "Details", close: "Close", resend: "Resend", closed: "Sales closed", eodDone: "Today's sales have been closed", depositDone: "Deposit already entered — POS locked",
  noStock: "No initial stock set for today. Ask Bar Team / Superadmin to save Rider Stock first.", thankYou: "Thank you!", items: "Items", transactions: "transactions",
  estProfit: "Est. Profit", revenue: "Revenue", customers: "Customers", tapProducts: "Tap products to add them", selectMenus: "Select menus", appsScript: "Google Apps Script URL",
  permissions: "Permissions", appearance: "Appearance & language", motivation: "Keep up the sales!", userInfo: "User Info",
  textFont: "Text & Font", textSize: "Text Size", boldText: "Bold Text", textColor: "Text Color", fontType: "Font Type", defaultFont: "Default",
};
const id = {
  dashboard: "Dashboard", inventory: "Inventaris", menuStock: "Stock Menu Production", posDashboard: "Dashboard POS", pos: "POS", riderStock: "Stock Awal", stockRider: "Stock Rider", stockPickup: "Pengambilan", stockRemaining: "Sisa", deposit: "Setoran",
  invoice: "Invoice", riderDash: "Dasbor Rider", handover: "Transfer / Serah Terima Kas", finance: "Laporan Keuangan", salary: "Target Rank Rider", profile: "Profil",
  settings: "Pengaturan", reports: "Laporan", purchaseOrders: "Purchase Order", broadcast: "Broadcast", paymentAccounts: "Akun Pembayaran", more: "Lainnya", logout: "Keluar", main: "Utama", stock: "Stok", today: "Hari Ini", yesterday: "Kemarin", week: "Minggu Ini", month: "Bulan Ini",
  prevmonth: "Bulan Lalu", prevweek: "Minggu Kemarin", custom: "Manual", cupsSold: "Cup Terjual", cashRevenue: "Pendapatan Cash", qrisRevenue: "Pendapatan QRIS", expenses: "Pengeluaran",
  save: "Simpan", cancel: "Batal", sendWA: "Kirim ke WhatsApp", download: "Unduh", login: "Masuk", username: "Username atau Email", password: "Kata Sandi",
  remember: "Ingat saya di perangkat ini", pin: "PIN", enterPin: "Masukkan PIN untuk membuka kasir", selectRider: "Pilih Rider", allRiders: "Semua Rider",
  date: "Tanggal", time: "Waktu", total: "Total", remaining: "Sisa", price: "Harga", qty: "Jml", saveRider: "Simpan Data Rider", welcome: "Selamat datang kembali",
  darkMode: "Mode Gelap", lightMode: "Mode Terang", language: "Bahasa", notifications: "Notifikasi", gps: "GPS (Rider saja)", whileUsing: "Izinkan Saat Aplikasi Digunakan",
  lowStock: "Stok menipis", checkIn: "Absen Masuk", checkOut: "Absen Pulang", endDay: "Tutup Penjualan Hari Ini", history: "Riwayat Penjualan", customer: "Pelanggan",
  cashReceived: "Uang Diterima", change: "Kembalian", checkout: "Bayar", receipt: "Struk", newDeposit: "Setoran Baru", incentive: "Insentif",
  attendance: "Hari Hadir", gross: "Pendapatan Kotor", placement: "Lokasi", joined: "Bergabung", nextTier: "Kategori Berikutnya", bestSelling: "Produk Terlaris",
  activeRiders: "Rider Bertugas", income: "Uang Masuk", outgo: "Uang Keluar", balance: "Saldo", addExpense: "Tambah Pengeluaran", noData: "Tidak ada data untuk periode ini", category: "Kategori",
  rider: "Rider", pic: "PIC", menu: "Menu", wastage: "Wastage", sold: "Terjual", diff: "Selisih", minus: "Minus", cash: "Cash", qris: "QRIS", totalIncome: "Total Pendapatan",
  totalSold: "Total Terjual", newDebt: "Hutang Baru", initialDebt: "Hutang Awal", remainingDebt: "Sisa Hutang", debtPayment: "Bayar Hutang", netCash: "Setoran Bersih",
  commission: "Komisi Rider", saveDb: "Simpan ke Database", photoEvidence: "Bukti Foto", photoRequired: "Bukti foto wajib diambil", takePhoto: "Ambil Foto",
  stockReport: "Laporan Stok", orderItems: "Pesanan Barang", material: "Bahan Baku", type: "Tipe", note: "Catatan", status: "Status", recipes: "Resep", production: "Produksi",
  bundling: "Bundling", cups: "cup", paid: "LUNAS", unpaid: "BELUM LUNAS", downPayment: "Uang Muka / DP", remainingPayment: "Sisa Pembayaran", createInvoice: "Buat Invoice",
  dailyAllowance: "Uang Harian", withdraw: "Tarik", withdrawals: "Riwayat Penarikan", method: "Metode", bank: "Rekening Bank", amount: "Jumlah", available: "Tersedia",
  totalCups: "Total Cup Terjual", dailySales: "Penjualan Harian", exportPdf: "Ekspor PDF", print: "Cetak", excel: "Excel", expectedCash: "Kas yang Seharusnya Diterima",
  receivedCash: "Total Kas Diterima", difference: "Selisih", addLine: "Tambah baris", giver: "PIC Pemberi (Bar Team)", receiver: "PIC Penerima", handoverDate: "Tanggal Serah Terima",
  period: "Periode", details: "Detail", close: "Tutup", resend: "Kirim Ulang", closed: "Penjualan ditutup", eodDone: "Penjualan hari ini sudah ditutup", depositDone: "Setoran sudah diinput — POS terkunci",
  noStock: "Belum ada stok awal hari ini. Minta Bar Team / Superadmin menyimpan Stok Rider dulu.", thankYou: "Terima kasih!", items: "Item", transactions: "transaksi",
  estProfit: "Est. Laba", revenue: "Pendapatan", customers: "Pelanggan", tapProducts: "Ketuk produk untuk menambahkan", selectMenus: "Pilih menu", appsScript: "URL Google Apps Script",
  permissions: "Hak Akses", appearance: "Tampilan & bahasa", motivation: "Semangat jualannya!", userInfo: "Info Pengguna",
  textFont: "Teks & Font", textSize: "Ukuran Teks", boldText: "Teks Tebal", textColor: "Warna Teks", fontType: "Jenis Font", defaultFont: "Bawaan",
};
const ja = {
  dashboard: "メインダッシュボード", inventory: "在庫", menuStock: "メニュー在庫", pos: "レジ(POS)", riderStock: "ライダー在庫", deposit: "入金",
  invoice: "請求書", riderDash: "ライダーダッシュボード", handover: "現金引き渡し", finance: "財務レポート", salary: "給与・インセンティブ", profile: "プロフィール",
  settings: "設定", more: "その他", logout: "ログアウト", main: "メイン", stock: "在庫", today: "今日", yesterday: "昨日", week: "今週", month: "今月",
  prevmonth: "先月", custom: "カスタム", cupsSold: "販売カップ数", cashRevenue: "現金売上", qrisRevenue: "QRIS売上", expenses: "経費",
  save: "保存", cancel: "キャンセル", sendWA: "WhatsAppで送信", download: "ダウンロード", login: "ログイン", username: "ユーザー名またはメール", password: "パスワード",
  remember: "この端末で記憶する", pin: "PIN", enterPin: "レジを開くにはPINを入力", selectRider: "ライダー選択", allRiders: "全ライダー",
  date: "日付", time: "時間", total: "合計", remaining: "残り", price: "価格", qty: "数量", saveRider: "ライダー情報を保存", welcome: "おかえりなさい",
  darkMode: "ダークモード", lightMode: "ライトモード", language: "言語", notifications: "通知", gps: "GPS(ライダーのみ)", whileUsing: "アプリ使用中のみ許可",
  lowStock: "在庫少", checkIn: "出勤", checkOut: "退勤", endDay: "本日の売上を締める", history: "売上履歴", customer: "顧客",
  cashReceived: "受取現金", change: "おつり", checkout: "支払う", receipt: "レシート", newDeposit: "新規入金", incentive: "インセンティブ",
  attendance: "出勤日数", gross: "総売上", placement: "配置", joined: "参加日", nextTier: "次のランク", bestSelling: "人気商品",
  activeRiders: "稼働ライダー", income: "収入", outgo: "支出", balance: "残高", addExpense: "経費追加", noData: "この期間のデータはありません", category: "カテゴリ",
  rider: "ライダー", pic: "担当", menu: "メニュー", wastage: "廃棄", sold: "販売", diff: "差", minus: "マイナス", cash: "現金", qris: "QRIS", totalIncome: "総収入",
  totalSold: "総販売", newDebt: "新規負債", initialDebt: "初期負債", remainingDebt: "残債", debtPayment: "返済", netCash: "純入金",
  commission: "ライダー歩合", saveDb: "データベースに保存", photoEvidence: "写真証拠", photoRequired: "写真の証拠が必要です", takePhoto: "写真を撮る",
  stockReport: "在庫レポート", orderItems: "注文品", material: "材料", type: "種類", note: "メモ", status: "状態", recipes: "レシピ", production: "生産",
  bundling: "セット販売", cups: "カップ", paid: "支払済", unpaid: "未払い", downPayment: "手付金", remainingPayment: "残額", createInvoice: "請求書作成",
  dailyAllowance: "日当", withdraw: "引出", withdrawals: "引出履歴", method: "方法", bank: "銀行口座", amount: "金額", available: "利用可能",
  totalCups: "総販売カップ", dailySales: "日次売上", exportPdf: "PDF出力", print: "印刷", excel: "Excel", expectedCash: "受取予定現金",
  receivedCash: "受取現金合計", difference: "差額", addLine: "行を追加", giver: "引渡担当(バー)", receiver: "受取担当", handoverDate: "引渡日",
  period: "期間", details: "詳細", close: "閉じる", resend: "再送信", closed: "売上締め済", eodDone: "本日の売上は締められました", depositDone: "入金済み — レジロック",
  noStock: "本日の初期在庫がありません。先にライダー在庫を保存してください。", thankYou: "ありがとうございます！", items: "品目", transactions: "取引",
  estProfit: "推定利益", revenue: "売上", customers: "顧客", tapProducts: "商品をタップして追加", selectMenus: "メニュー選択", appsScript: "Google Apps Script URL",
  permissions: "権限", appearance: "外観と言語", motivation: "販売がんばって！",
  textFont: "文字とフォント", textSize: "文字サイズ", boldText: "太字", textColor: "文字色", fontType: "フォント", defaultFont: "デフォルト",
};
const zh = {
  dashboard: "主仪表板", inventory: "库存", menuStock: "菜单库存", pos: "收银台", riderStock: "骑手库存", deposit: "存款",
  invoice: "发票", riderDash: "骑手仪表板", handover: "现金交接", finance: "财务报告", salary: "工资与奖金", profile: "个人资料",
  settings: "设置", more: "更多", logout: "退出", main: "主要", stock: "库存", today: "今天", yesterday: "昨天", week: "本周", month: "本月",
  prevmonth: "上月", custom: "自定义", cupsSold: "已售杯数", cashRevenue: "现金收入", qrisRevenue: "QRIS收入", expenses: "支出",
  save: "保存", cancel: "取消", sendWA: "发送到WhatsApp", download: "下载", login: "登录", username: "用户名或邮箱", password: "密码",
  remember: "在此设备记住我", pin: "PIN", enterPin: "输入PIN以打开收银台", selectRider: "选择骑手", allRiders: "所有骑手",
  date: "日期", time: "时间", total: "合计", remaining: "剩余", price: "价格", qty: "数量", saveRider: "保存骑手数据", welcome: "欢迎回来",
  darkMode: "深色模式", lightMode: "浅色模式", language: "语言", notifications: "通知", gps: "GPS(仅骑手)", whileUsing: "仅在使用时允许",
  lowStock: "库存不足", checkIn: "签到", checkOut: "签退", endDay: "结束今日销售", history: "销售历史", customer: "顾客",
  cashReceived: "收到现金", change: "找零", checkout: "支付", receipt: "收据", newDeposit: "新存款", incentive: "奖金",
  attendance: "出勤天数", gross: "总收入", placement: "位置", joined: "加入", nextTier: "下一级别", bestSelling: "畅销产品",
  activeRiders: "在岗骑手", income: "收入", outgo: "支出", balance: "余额", addExpense: "添加支出", noData: "此期间没有数据", category: "类别",
  rider: "骑手", pic: "负责人", menu: "菜单", wastage: "损耗", sold: "已售", diff: "差异", minus: "减", cash: "现金", qris: "QRIS", totalIncome: "总收入",
  totalSold: "总销售", newDebt: "新债务", initialDebt: "初始债务", remainingDebt: "剩余债务", debtPayment: "还款", netCash: "净存款",
  commission: "骑手佣金", saveDb: "保存到数据库", photoEvidence: "照片证据", photoRequired: "需要照片证据", takePhoto: "拍照",
  stockReport: "库存报告", orderItems: "订购物品", material: "原料", type: "类型", note: "备注", status: "状态", recipes: "配方", production: "生产",
  bundling: "捆绑", cups: "杯", paid: "已付", unpaid: "未付", downPayment: "定金", remainingPayment: "余款", createInvoice: "创建发票",
  dailyAllowance: "每日津贴", withdraw: "提取", withdrawals: "提取历史", method: "方式", bank: "银行账户", amount: "金额", available: "可用",
  totalCups: "总售杯数", dailySales: "每日销售", exportPdf: "导出PDF", print: "打印", excel: "Excel", expectedCash: "应收现金",
  receivedCash: "收到现金合计", difference: "差额", addLine: "添加行", giver: "交付人(吧台)", receiver: "接收人", handoverDate: "交接日期",
  period: "期间", details: "详情", close: "关闭", resend: "重新发送", closed: "销售已结束", eodDone: "今日销售已结束", depositDone: "已存款 — 收银台锁定",
  noStock: "今日尚无初始库存。请先让吧台/管理员保存骑手库存。", thankYou: "谢谢！", items: "项目", transactions: "笔交易",
  estProfit: "预计利润", revenue: "收入", customers: "顾客", tapProducts: "点按产品以添加", selectMenus: "选择菜单", appsScript: "Google Apps Script网址",
  permissions: "权限", appearance: "外观与语言", motivation: "加油销售！",
  textFont: "文字与字体", textSize: "文字大小", boldText: "加粗", textColor: "文字颜色", fontType: "字体", defaultFont: "默认",
};
const ar = {
  dashboard: "لوحة التحكم الرئيسية", inventory: "المخزون", menuStock: "مخزون القائمة", pos: "نقطة البيع", riderStock: "مخزون السائق", deposit: "الإيداع",
  invoice: "فاتورة", riderDash: "لوحة السائق", handover: "تسليم النقد", finance: "التقرير المالي", salary: "الراتب والحوافز", profile: "الملف الشخصي",
  settings: "الإعدادات", more: "المزيد", logout: "تسجيل الخروج", main: "رئيسي", stock: "المخزون", today: "اليوم", yesterday: "أمس", week: "هذا الأسبوع", month: "هذا الشهر",
  prevmonth: "الشهر الماضي", custom: "مخصص", cupsSold: "الأكواب المباعة", cashRevenue: "إيرادات نقدية", qrisRevenue: "إيرادات QRIS", expenses: "المصروفات",
  save: "حفظ", cancel: "إلغاء", sendWA: "إرسال إلى واتساب", download: "تنزيل", login: "تسجيل الدخول", username: "اسم المستخدم أو البريد", password: "كلمة المرور",
  remember: "تذكرني على هذا الجهاز", pin: "الرقم السري", enterPin: "أدخل الرقم السري لفتح الكاشير", selectRider: "اختر السائق", allRiders: "كل السائقين",
  date: "التاريخ", time: "الوقت", total: "الإجمالي", remaining: "المتبقي", price: "السعر", qty: "الكمية", saveRider: "حفظ بيانات السائق", welcome: "مرحبًا بعودتك",
  darkMode: "الوضع الداكن", lightMode: "الوضع الفاتح", language: "اللغة", notifications: "الإشعارات", gps: "GPS (للسائق فقط)", whileUsing: "السماح أثناء الاستخدام",
  lowStock: "مخزون منخفض", checkIn: "تسجيل الحضور", checkOut: "تسجيل الانصراف", endDay: "إغلاق مبيعات اليوم", history: "سجل المبيعات", customer: "العميل",
  cashReceived: "النقد المستلم", change: "الباقي", checkout: "ادفع", receipt: "الإيصال", newDeposit: "إيداع جديد", incentive: "حافز",
  attendance: "أيام الحضور", gross: "الإيراد الإجمالي", placement: "الموقع", joined: "انضم", nextTier: "المستوى التالي", bestSelling: "الأكثر مبيعًا",
  activeRiders: "السائقون العاملون", income: "الدخل", outgo: "المصروف", balance: "الرصيد", addExpense: "إضافة مصروف", noData: "لا توجد بيانات لهذه الفترة", category: "الفئة",
  rider: "السائق", pic: "المسؤول", menu: "القائمة", wastage: "الهدر", sold: "مباع", diff: "الفرق", minus: "ناقص", cash: "نقد", qris: "QRIS", totalIncome: "إجمالي الدخل",
  totalSold: "إجمالي المبيعات", newDebt: "دين جديد", initialDebt: "الدين الأولي", remainingDebt: "الدين المتبقي", debtPayment: "سداد الدين", netCash: "صافي الإيداع",
  commission: "عمولة السائق", saveDb: "حفظ في قاعدة البيانات", photoEvidence: "دليل مصور", photoRequired: "الدليل المصور مطلوب", takePhoto: "التقاط صورة",
  stockReport: "تقرير المخزون", orderItems: "طلب المواد", material: "المادة", type: "النوع", note: "ملاحظة", status: "الحالة", recipes: "الوصفات", production: "الإنتاج",
  bundling: "الحزم", cups: "أكواب", paid: "مدفوع", unpaid: "غير مدفوع", downPayment: "دفعة مقدمة", remainingPayment: "المبلغ المتبقي", createInvoice: "إنشاء فاتورة",
  dailyAllowance: "بدل يومي", withdraw: "سحب", withdrawals: "سجل السحب", method: "الطريقة", bank: "حساب بنكي", amount: "المبلغ", available: "متاح",
  totalCups: "إجمالي الأكواب المباعة", dailySales: "المبيعات اليومية", exportPdf: "تصدير PDF", print: "طباعة", excel: "Excel", expectedCash: "النقد المتوقع",
  receivedCash: "إجمالي النقد المستلم", difference: "الفرق", addLine: "إضافة سطر", giver: "المسلّم (فريق البار)", receiver: "المستلم", handoverDate: "تاريخ التسليم",
  period: "الفترة", details: "التفاصيل", close: "إغلاق", resend: "إعادة الإرسال", closed: "تم إغلاق المبيعات", eodDone: "تم إغلاق مبيعات اليوم", depositDone: "تم الإيداع — الكاشير مقفل",
  noStock: "لا يوجد مخزون مبدئي لليوم. اطلب من فريق البار/المشرف حفظ مخزون السائق أولاً.", thankYou: "شكرًا لك!", items: "عناصر", transactions: "معاملات",
  estProfit: "الربح المتوقع", revenue: "الإيراد", customers: "العملاء", tapProducts: "انقر المنتجات لإضافتها", selectMenus: "اختر القوائم", appsScript: "رابط Google Apps Script",
  permissions: "الصلاحيات", appearance: "المظهر واللغة", motivation: "واصل البيع!",
  textFont: "النص والخط", textSize: "حجم النص", boldText: "غامق", textColor: "لون النص", fontType: "الخط", defaultFont: "افتراضي",
};
const dict = { en, id, ja, zh, ar };

export const LANGS = [["id", "Indonesia"], ["en", "English"], ["ja", "日本語"], ["zh", "中文"], ["ar", "العربية"]];

const LangCtx = createContext({ lang: "id", setLang: () => {}, t: (k) => k });

function applyDir(l) {
  document.documentElement.dir = l === "ar" ? "rtl" : "ltr";
  document.documentElement.lang = l;
}

export function LangProvider({ children }) {
  const [lang, setLangState] = useState(localStorage.getItem("si4am_lang") || "id");
  useEffect(() => { applyDir(lang); }, [lang]);
  const setLang = (l) => { localStorage.setItem("si4am_lang", l); setLangState(l); };
  const t = (k) => dict[lang]?.[k] ?? en[k] ?? k;
  return <LangCtx.Provider value={{ lang, setLang, t }}>{children}</LangCtx.Provider>;
}

export const useT = () => useContext(LangCtx);
