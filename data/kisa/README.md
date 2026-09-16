# kisa

KISA 주요정보통신기반시설 기술적 취약점 점검항목 데이터 디렉터리.

```
kisa/
└── linux/
    ├── account.yaml     # 계정 관리 (U-01 ~ U-13)
    ├── file.yaml        # 파일 및 디렉토리 관리 (U-14 ~ U-33)
    ├── service.yaml     # 서비스 관리 (U-34 ~ U-63)
    ├── patch.yaml       # 패치 관리 (U-64)
    └── logging.yaml     # 로그 관리 (U-65 ~ U-67)
```

- **원본 SSOT.** 출처는 KISA 기술적 취약점 분석·평가 방법 상세가이드(2026) "01. Unix 서버" 장.
- 각 항목은 `id / name / severity / target / purpose / pass / fail / automation / evidence / isms_p`를 담는다.
- `pass`/`fail`은 가이드 원문의 "양호/취약" 판단 기준이다.

> 이 디렉터리는 원본에서 추출한 사실이므로 수정하지 않는다. Technical Check는 `data/checks/`에 별도로 정의한다.
