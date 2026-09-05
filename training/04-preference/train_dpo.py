"""DPO on a real model, dpo.py at full size.

dpo.py moves a grid toward chosen words and away from rejected ones,
relative to a frozen reference. This does the same to an open model on
a file of preference pairs, each line a prompt, a chosen answer and a
rejected answer. trl holds the loss from dpo.py, the reference model,
and the training loop. The adapter from chapter 2 is the usual starting
point, because preference tuning is the third round and instruction
tuning is the second.

It needs a GPU and is not run in CI. --cpu runs it with no card, slowly,
for watching it work once. One step on sixteen pairs took fifty nine
minutes that way, about three and a half times a step of chapter 2,
because a preference step runs both the model and the frozen reference.
That one step reported a loss of 0.6914, which is the 0.693 chapter 20
opens with, measured on a real model rather than on the demo.

    pip install "agentpath-kit[training]"
    python train_dpo.py pairs.jsonl --model adapter-merged --output dpo-adapter

The pairs file is the shape trl reads. Each line holds prompt, chosen
and rejected, and chosen and rejected are messages lists or plain
strings.
"""
import argparse


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pairs", help="JSONL with prompt, chosen and rejected per line")
    parser.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--output", default="dpo-adapter")
    parser.add_argument("--beta", type=float, default=0.1, help="the leash from dpo.py")
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument(
        "--cpu",
        action="store_true",
        help="run without a GPU, slowly, which is enough to watch it work once",
    )
    arguments = parser.parse_args(argv)

    from datasets import load_dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import DPOConfig, DPOTrainer

    tokenizer = AutoTokenizer.from_pretrained(arguments.model)
    model = AutoModelForCausalLM.from_pretrained(arguments.model, torch_dtype="auto")
    data = load_dataset("json", data_files=arguments.pairs, split="train")

    # With LoRA adapters the reference model is the same weights with the
    # adapters switched off, so trl does not need a second copy in memory.
    # That is the reference term of dpo.py, and it is why DPO with LoRA
    # fits where DPO with full fine tuning would not.
    adapters = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        task_type="CAUSAL_LM",
    )
    # beta is a tenth here where dpo.py used one, because a real model's
    # log probabilities are sums over hundreds of tokens and the margins
    # are correspondingly larger. The learning rate is a quarter of
    # chapter 2's. The adapters still start at zero, which argues for a
    # high rate, but this is a nudge to a model that already works, not
    # a lesson from scratch, and that argues for a lower one.
    settings = DPOConfig(
        output_dir=arguments.output,
        beta=arguments.beta,
        num_train_epochs=arguments.epochs,
        learning_rate=5e-5,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,
        logging_steps=10,
        # bf16 is a GPU number format, so asking for it without a card stops
        # the run before it starts. --cpu turns it off, the same escape
        # train_lora.py has, and it costs the same hours.
        bf16=not arguments.cpu,
        use_cpu=arguments.cpu,
        max_length=2048,
    )
    trainer = DPOTrainer(
        model=model,
        ref_model=None,
        args=settings,
        train_dataset=data,
        processing_class=tokenizer,
        peft_config=adapters,
    )
    trainer.train()
    trainer.save_model(arguments.output)
    print(f"preference adapter saved to {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
