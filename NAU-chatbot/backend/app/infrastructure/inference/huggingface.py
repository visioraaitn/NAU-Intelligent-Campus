from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import torch
from peft import PeftConfig, PeftModel
from sentence_transformers import CrossEncoder, SentenceTransformer
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from app.core.file_config import ModelRoleConfig
from app.services.llm.providers import LLMMessage


def clean_output(value: str) -> str:
    value = re.sub(r"<think>.*?</think>", "", value, flags=re.DOTALL)
    return value.replace("<think>", "").replace("</think>", "").strip()


def _source(config: ModelRoleConfig) -> str:
    return config.local_path.strip() or config.model_id


def _quantization(config: ModelRoleConfig) -> BitsAndBytesConfig | None:
    if config.quantization == "8bit":
        return BitsAndBytesConfig(load_in_8bit=True)
    if config.quantization != "4bit":
        return None
    dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16
    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=dtype,
    )


class HuggingFaceLLM:
    def __init__(self, config: ModelRoleConfig, *, allow_adapter: bool) -> None:
        source = _source(config)
        common: dict[str, Any] = {
            "local_files_only": config.local_files_only,
            "trust_remote_code": config.trust_remote_code,
        }
        if config.revision:
            common["revision"] = config.revision
        quantization = _quantization(config)
        is_adapter = allow_adapter and (
            (Path(source).is_dir() and (Path(source) / "adapter_config.json").exists())
            or self._is_cached_adapter(source, config.local_files_only)
        )
        if is_adapter:
            peft_config = PeftConfig.from_pretrained(
                source,
                local_files_only=config.local_files_only,
            )
            base = peft_config.base_model_name_or_path
            self.tokenizer = AutoTokenizer.from_pretrained(base, **common)
            base_model = AutoModelForCausalLM.from_pretrained(
                base,
                quantization_config=quantization,
                device_map=config.device,
                low_cpu_mem_usage=True,
                **common,
            )
            self.model = PeftModel.from_pretrained(
                base_model,
                source,
                local_files_only=config.local_files_only,
            )
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(source, **common)
            self.model = AutoModelForCausalLM.from_pretrained(
                source,
                quantization_config=quantization,
                device_map=config.device,
                low_cpu_mem_usage=True,
                **common,
            )
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
        self.model.eval()

    @staticmethod
    def _is_cached_adapter(source: str, local_only: bool) -> bool:
        try:
            PeftConfig.from_pretrained(source, local_files_only=local_only)
            return True
        except Exception:
            return False

    def generate(self, messages: Sequence[LLMMessage], max_new_tokens: int) -> str:
        chat = [{"role": item.role, "content": item.content} for item in messages]
        try:
            prompt = self.tokenizer.apply_chat_template(
                chat,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except TypeError:
            prompt = self.tokenizer.apply_chat_template(
                chat,
                tokenize=False,
                add_generation_prompt=True,
            )
        encoded = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=min(getattr(self.tokenizer, "model_max_length", 8192), 8192),
        )
        device = self.model.get_input_embeddings().weight.device
        encoded = {name: value.to(device) for name, value in encoded.items()}
        input_length = encoded["input_ids"].shape[1]
        with torch.inference_mode():
            output = self.model.generate(
                **encoded,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                repetition_penalty=1.05,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )
        return clean_output(
            self.tokenizer.decode(output[0][input_length:], skip_special_tokens=True)
        )


class HuggingFaceEmbedding:
    def __init__(self, config: ModelRoleConfig) -> None:
        self.model = SentenceTransformer(
            _source(config),
            device=config.device,
            local_files_only=config.local_files_only,
            trust_remote_code=config.trust_remote_code,
        )

    def embed(self, texts: Sequence[str], *, query: bool = False) -> list[list[float]]:
        prefix = "query" if query else "passage"
        prefixed = [f"{prefix}: {text}" for text in texts]
        result = self.model.encode(prefixed, normalize_embeddings=True)
        return result.tolist()


class HuggingFaceReranker:
    def __init__(self, config: ModelRoleConfig) -> None:
        self.model = CrossEncoder(
            _source(config),
            device=config.device,
            local_files_only=config.local_files_only,
            trust_remote_code=config.trust_remote_code,
            revision=config.revision,
        )

    def rerank(self, query: str, documents: Sequence[str]) -> list[float]:
        scores = self.model.predict([(query, document) for document in documents])
        return [float(score) for score in scores]
