# darklink
# 2019-03-31
# Dark chain detection 
#change 2019/05/21:
#    1、针对mate标签无法扫描IP类型的网址暗链处理
    
#change 2019/05/14:
#    1、针对无法扫除<a>标签里面包含margin-left内容的暗链
#    2、A_Reg_Href参数属性里面添加一个网站的后缀（\.in）

#change 2019/04/03
# 过滤内容<a target="_blank" class="buy" href="http://www.xxxx.com" style="text-decoration:none;">您的域名已经到期，请联系您的服务商续费</a>


#change 2019/01/04
# 白名单改为命令行传入

#change 2018/11/01
# 添加白名单文件

#change 2018/08/21
# 暗链特征：
# 	超链接a的属性display:none|visibility:hidden
# 	这个根据颜色来判断的，不是很准确，待定
# 	div设置属性font-size:0px
# 	div的属性display:none|visibility:hidden
# 	marquee的scrollamount的属性，测试发现高于1000就很难发现了，所以这里目前暂定1000
# 	位置属性text-indent
# 	利用位置position:absolute、top/left
# 	利用位置position:absolute、top/right
# 	利用位置position:absolute、z-index
# 	利用位置position:fixed、top/left
# 	利用位置position:fixed、top/right
# 	利用位置position:fixed、z-index
