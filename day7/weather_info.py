
xy = '''(x,y) 지역명
(60, 27) 서울특별시
(98, 76) 부산광역시
(89, 90) 대구광역시
(55, 124) 인천광역시
(58, 74) 광주광역시
(67, 100) 대전광역시
(102, 84) 울산광역시
(66, 103) 세종시
(60, 120) 경기도
(69, 107) 충청북도
(68, 100) 충청남도
(51, 67) 전라남도
(87, 106) 경상북도
(91, 77) 경상남도
(52, 38) 제주도
(73, 134) 강원도
(63, 89) 전라북도 
'''

get_ultra_weather_schema = {
  "type": "function",
  "function": {
    "name": "get_ultra_weather",
    "description": "초단기 실황 날씨 정보를 조회합니다.",
    "parameters": {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "enum": ["ultra"],
                "description": "초단기 실황"
            },
            "region": {
                "type": "string",
                "description": "지역명 (예: 서울)"
            },
            "x": {
                "type": "integer",
                "description": f"격자 X 좌표 지역별 좌표는 다음을 참고 {xy}"
            },
            "y": {
                "type": "integer",
                "description": f"격자 Y 좌표 지역별 좌표는 다음을 참고 {xy}"
            },
            "base_time": {
                "type": "string",
                "description": "API 기준 시각 (예: 202508051800). 기준 시각은 정시. 현재시간보다 빠르면 안됨 적어도 한시간 이전 시간 선택"
            },
        },
        "required": ["type", "region", "x", "y", "base_time"]
    }
  }
}



get_short_weather_schema = {
  "type": "function",
  "function": {
    "name": "get_short_weather",
    "description": "단기 예보 날씨 정보를 조회합니다.",
    "parameters": {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "enum": ["short"],
                "description": "단기 예보"
            },
            "region": {
                "type": "string",
                "description": "지역명 (예: 서울)"
            },
            "x": {
                "type": "integer",
                "description": f"격자 X 좌표 지역별 좌표는 다음을 참고 {xy}"
            },
            "y": {
                "type": "integer",
                "description": f"격자 Y 좌표 지역별 좌표는 다음을 참고 {xy}"
            },
            "base_time": {
                "type": "string",
                "description": "API 기준 시각 (예: 202508051800) - 가능한 시간은 다음을 참고 Base_time : 0200, 0500, 0800, 1100, 1400, 1700, 2000, 2300 (1일 8회. 반드시 다음 8개중 현재와 가까운 것 택 1. 현재시간보다 빠르면 안됨.) "
            },
        },
        "required": ["type", "region", "x", "y", "base_time"]
    }
  }
}

reg_codes = '''105	강원도
108	전국
109	서울, 인천, 경기도
131	충청북도
133	대전, 세종, 충청남도
146	전북자치도
156	광주, 전라남도
143	대구, 경상북도
159	부산, 울산, 경상남도
184	제주도
'''

get_mid_weather_schema = {
  "type": "function",
  "function" : {
    "name": "get_mid_weather",
    "description": "중기 예보 날씨 정보를 조회합니다.",
    "parameters": {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "enum": ["mid"],
                "description": "중기 예보"
            },
            "region": {
                "type": "string",
                "description": "지역명 (예: 서울)"
            },
            "region_code": {
                "type": "string",
                "description": f"중기 예보용 지역 코드 {reg_codes}"
            },
            "base_time": {
                "type": "string",
                "description": "API 기준 시각 (예: 202508051800). 06시 또는 18시"  
            },
        },
        "required": ["type", "region", "region_code", "base_time"]
    }
  }
}



short_code_info = '''

예보 요소	정성정보 코드값	정성정보
용어	정성정보 의미
강수량
(PCP)	1	약한 비	시간당 3mm 미만의 약한 비
	2	보통 비	시간당 3mm 이상 15mm 미만의 보통 비
	3	강한 비	시간당 15mm 이상의 강한 비
눈의양
(SNO)	1	보통 눈	시간당 1cm 미만의 보통 눈
	2	많은 눈	시간당 1cm 이상의 많은 눈
풍  속
(WSD)	1	약한 바람	4m/s 이상의 약한 바람
	2	약간 강한 바람	4m/s 이상 9m/s 미만의 약간 강한 바람
	3	강한 바람	9m/s 이상의 강한 바람


항목값	항목명	단위	압축bit수
POP	강수확률	%	8
PTY	강수형태	코드값	4
PCP	1시간 강수량	범주 (1 mm)	8
REH	습도	%	8
SNO	1시간 신적설	범주(1 cm)	8
SKY	하늘상태	코드값	4
TMP	1시간 기온	℃	10
TMN	일 최저기온	℃	10
TMX	일 최고기온	℃	10
UUU	풍속(동서성분)	m/s	12
VVV	풍속(남북성분)	m/s	12
WAV	파고	M	8
VEC	풍향	deg	10
WSD	풍속	m/s	10

'''

ultra_code_info = '''

T1H	기온	℃	10
RN1	1시간 강수량	범주 (1 mm)	8
SKY	하늘상태	코드값	4
UUU	동서바람성분	m/s	12
VVV	남북바람성분	m/s	12
REH	습도	%	8
PTY	강수형태	코드값	4
LGT	낙뢰	kA(킬로암페어)	4
VEC	풍향	deg	10
WSD	풍속	m/s	10


'''

