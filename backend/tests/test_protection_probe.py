def test_intentional_failure_for_branch_protection_probe():
    # ブランチ保護の動作確認用に、わざと失敗させるテスト。
    # 確認後にこのファイルごと削除する。
    assert False, "intentional failure to verify branch protection blocks merge"
