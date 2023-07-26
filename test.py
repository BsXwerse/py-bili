import qrcode

qr = qrcode.QRCode()
qr.add_data("https://www.baidu.com")
#invert=True白底黑块,有些app不识别黑底白块.
qr.print_ascii(invert=True)
input("aaaaaaa")
