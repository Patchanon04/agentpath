"""Load a real model at four bits, and train LoRA on top of it, which is QLoRA.

quantize.py rounds a grid and measures what it costs. This loads an open
model with every grid stored at four bits, the grouped kind from
quantize.py with a group of sixty four, and reports the memory it takes
against the sixteen bit figure. With --train it adds LoRA adapters on
top and runs chapter 2's training, which is QLoRA. The base stays at
four bits and frozen, the adapters are trained at sixteen, and a model
that needed a twenty gigabyte card fits in ten.

It needs an NVIDIA GPU and the bitsandbytes library, which is easier
to install on Linux than on Windows, and it is not run in CI.

    pip install "agentpath-kit[training]" bitsandbytes
    python load_4bit.py --model Qwen/Qwen2.5-7B-Instruct
    python load_4bit.py --model Qwen/Qwen2.5-7B-Instruct --train clean.jsonl
"""
import argparse


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--train", help="chat JSONL from chapter 1, to run QLoRA on top")
    parser.add_argument("--output", default="qlora-adapter")
    arguments = parser.parse_args(argv)

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    # nf4 is a four bit format whose sixteen levels are placed where the
    # weights of a trained model actually cluster, rather than evenly, so
    # it loses less than the plain rounding in quantize.py. The double
    # quantization flag quantizes the scales themselves, saving a little
    # more. The compute dtype is what the four bit numbers are expanded
    # to on the way into each matrix multiply, dequantize in quantize.py.
    four_bit = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    tokenizer = AutoTokenizer.from_pretrained(arguments.model)
    model = AutoModelForCausalLM.from_pretrained(
        arguments.model, quantization_config=four_bit, device_map="auto"
    )
    # Params4bit are packed two to a byte, so counting elements of the
    # parameters would report half the model. transformers knows this.
    used = model.get_memory_footprint() / 1024**3
    parameters = model.num_parameters()
    print(f"{parameters / 1e9:.1f} billion parameters using {used:.1f} GB at four bits")
    print(f"the same model at sixteen bits would need {parameters * 2 / 1024**3:.1f} GB")

    if not arguments.train:
        return 0

    from datasets import load_dataset
    from peft import LoraConfig, prepare_model_for_kbit_training
    from trl import SFTConfig, SFTTrainer

    # prepare_model_for_kbit_training freezes the four bit base, casts the
    # parameters that were not quantized, the norms and the output head,
    # to full precision for numerical stability, and turns on gradient
    # checkpointing, which is where most of the memory saving comes from.
    model = prepare_model_for_kbit_training(model)
    adapters = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"
        ],
        task_type="CAUSAL_LM",
    )
    data = load_dataset("json", data_files=arguments.train, split="train")
    settings = SFTConfig(
        output_dir=arguments.output,
        num_train_epochs=2,
        learning_rate=2e-4,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,
        logging_steps=10,
        bf16=True,
        max_length=2048,
    )
    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=data,
        peft_config=adapters,
        args=settings,
    )
    trainer.train()
    trainer.save_model(arguments.output)
    print(f"adapter saved to {arguments.output}, trained beside a four bit base")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
