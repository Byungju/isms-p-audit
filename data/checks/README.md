# checks

Technical Check 정의 디렉터리. `docs/design/check-specification.md` 설계를 따른다.

```
checks/
└── linux/
    ├── account.yaml     # 계정 관리 관련 Check (U-01, U-05 등)
    ├── file.yaml        # 파일/디렉토리 관련 Check (U-16 등)
    ├── service.yaml     # 서비스 관련 Check (U-34 등)
    └── patch.yaml       # 패치 관련 Check (U-64 등)
```

Technical Check는 KISA Item 자체가 아니라, **KISA Item을 판단하기 위한 하나의 구체적인 기술적 검사 단위**다.

- Check ID: `CK-<platform>-<kisa-id>-<sequence>` (예: `CK-lnx-U01-001`)
- Check 구조: `id / type / description / platforms / targets / expect / automation / evidence`
- KISA 원본 정보(title/severity/source/pass·fail)와 Check↔KISA 관계(mapping)는 여기에 저장하지 않는다.
- 실행 명령어(grep/awk/systemctl 등)를 포함하지 않는다. (명령은 향후 Implementation 계층)

> 하나의 KISA Item이 여러 Technical Check로 분해될 수 있다(예: U-01 → SSH/Telnet 2개 Check).
