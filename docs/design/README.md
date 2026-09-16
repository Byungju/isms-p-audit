# design

기술 점검(Check) 설계 문서를 담는 디렉터리.

```
design/
├── check-specification.md          # Check Specification 설계 기준 (현재 확정)
├── check-specification-validation.md # 설계 검증 (초기 5개 항목)
└── check-specification-review.md    # 실제 Check 데이터 검토 결과
```

각 문서의 역할:

- `check-specification.md` — **현재 채택된 설계의 기준 문서.** 구현자는 이 문서를 보고 Check Schema를 설계한다.
  - Check ID 규칙, Check 구조, targets/expect/file_mode/service mechanism/external reference, 상태 모델, Evidence 모델을 정의.
- `check-specification-validation.md` — 초기 설계를 대표 항목으로 검증한 과정과 발견된 문제를 기록한 문서.
- `check-specification-review.md` — `data/checks/`의 실제 Check 정의를 설계 기준으로 검토한 결과와, 향후 수정이 필요한 설계 문제를 기록.

> `check-specification.md`는 설계 기준이므로 신중히 변경하고, 검증·검토 이력은 별도 문서(`*-validation.md`, `*-review.md`)에 남긴다.
