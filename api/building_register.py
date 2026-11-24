"""Look up the MOLIT 건축HUB building title data for a report address."""
import re
import unicodedata
from datetime import datetime, timezone

from document_requests import DocumentRequestError
from real_estate_price_adapters import KAKAO_KEY_ENVS, env_key, pnu_from_address, request_xml
from registry_lookup import _address_key, _units

ENDPOINT = "https://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo"
SOURCE = "국토교통부 건축HUB · 건축물대장 표제부"
LOT_ADDRESS = re.compile(r"^(.+?(?:로|길|동|리|가|읍|면)\s+(?:산\s*)?\d+(?:-\d+)?)(?=$|[\s,(])")
KEY_NAMES = ("BUILDING_HUB_API_KEY", "MOLIT_SERVICE_KEY", "PUBLIC_DATA_API_KEY")


def _without_lot_suffix(address):
    return re.sub(r"(?<=\d)번지(?=$|[\s,(])", "", address)


def building_status():
    available = bool(env_key(*KEY_NAMES) and env_key(*KAKAO_KEY_ENVS))
    return {"available": available, "source": SOURCE, "reason": "" if available else
            "건축HUB 주소 조회가 연결되지 않았습니다. 보유한 건축물대장 PDF를 여기서 대조할 수 있습니다."}


def lookup_building(address):
    if not isinstance(address, str) or len(address) > 220:
        raise DocumentRequestError(400, "점검할 주소를 확인해 주세요.")
    address = _without_lot_suffix(" ".join(unicodedata.normalize("NFKC", address).split()))
    match = LOT_ADDRESS.match(address)
    target = _address_key(address)
    if not match or not target:
        raise DocumentRequestError(400, "시·군·구와 도로명·건물번호 또는 지번을 포함해 주세요.")
    status = building_status()
    if not status["available"]:
        raise DocumentRequestError(503, status["reason"])
    # A building-title query only needs the base address. Unit and floor are not sent to geocoding.
    pnu, _ = pnu_from_address(match.group(1))
    if not re.fullmatch(r"\d{10}[12]\d{8}", pnu):
        raise DocumentRequestError(422, "정확한 지번을 찾지 못했습니다. 점검할 도로명주소 또는 지번을 확인해 주세요.")
    lot = {"sigunguCd": pnu[:5], "bjdongCd": pnu[5:10], "platGbCd": "1" if pnu[10] == "2" else "0",
           "bun": pnu[11:15], "ji": pnu[15:]}
    try:
        root = request_xml(ENDPOINT, {**lot, "serviceKey": env_key(*KEY_NAMES), "numOfRows": "200", "pageNo": "1"})
        code = (root.findtext(".//header/resultCode") or "").strip()
        if code not in {"00", "000", "0000"} or root.find(".//body") is None:
            raise ValueError("provider response")
        count = int(root.findtext(".//body/totalCount") or "0")
    except Exception:
        raise DocumentRequestError(502, "건축HUB에서 표제부를 조회하지 못했습니다. 잠시 후 다시 시도해 주세요.") from None
    if count > 200:
        raise DocumentRequestError(422, "이 지번의 표제부가 많아 범위를 확인할 수 없습니다. 해당 동의 대장 PDF를 대조해 주세요.")

    blocks = _units(address)["동"]
    records = []
    for item in root.findall(".//body/items/item"):
        def field(name):
            return (item.findtext(name) or "").strip()

        road, land = field("newPlatPlc"), field("platPlc")
        if target not in {_address_key(road), _address_key(_without_lot_suffix(land))}:
            continue
        if any(field(name) and field(name).zfill(len(expected)) != expected for name, expected in lot.items()):
            continue
        dong = field("dongNm")
        if blocks and _units(" " + (dong if dong.endswith("동") else dong + "동"))["동"] != blocks:
            continue
        date_text = field("useAprDay")
        try:
            approved_at = datetime.strptime(date_text, "%Y%m%d").date().isoformat()
        except ValueError:
            approved_at = None
        records.append({"address": road or land, "buildingName": field("bldNm"), "dongName": dong,
                        "mainUse": field("mainPurpsCdNm"), "approvedAt": approved_at,
                        "aboveGroundFloors": field("grndFlrCnt")})
    return {"records": records, "checkedAt": datetime.now(timezone.utc).isoformat(), "source": SOURCE}
