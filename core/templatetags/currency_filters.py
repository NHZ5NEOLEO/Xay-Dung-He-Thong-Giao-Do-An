from decimal import Decimal
from django import template

register = template.Library()


@register.filter(name='dinh_dang_tien')
def dinh_dang_tien(value):
    """
    Định dạng số tiền có dấu chấm phân cách hàng nghìn.
    Ví dụ: 38000 -> "38.000"
    """
    if value is None or value == '':
        return ''
    try:
        val = int(round(float(value)))
        return f"{val:,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return value


@register.filter(name='tien_vnd')
@register.filter(name='currency_vn')
def tien_vnd(value):
    """
    Định dạng số tiền có dấu chấm phân cách hàng nghìn kèm chữ 'đ'.
    Ví dụ: 38000 -> "38.000đ"
    """
    res = dinh_dang_tien(value)
    if res == '':
        return ''
    return f"{res}đ"

