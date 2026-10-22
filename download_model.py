from huggingface_hub import snapshot_download

print("Скачивание модели GigaAM v3 ONNX (~900 МБ)...")
snapshot_download(
    repo_id="istupakov/gigaam-v3-onnx",
    allow_patterns=[
        "v3_e2e_rnnt_encoder.onnx",
        "v3_e2e_rnnt_decoder.onnx",
        "v3_e2e_rnnt_joint.onnx",
        "v3_e2e_rnnt_vocab.txt",
        "v3_e2e_rnnt.yaml",
        "config.json",
    ],
    local_dir="./gigaam-v3-e2e-rnnt-onnx",
    local_dir_use_symlinks=False,
)
print("Готово! Модель в папке gigaam-v3-e2e-rnnt-onnx")