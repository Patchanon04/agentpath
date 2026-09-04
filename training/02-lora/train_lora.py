"""LoRA fine tuning of a real model, the same idea as lora.py at full size.

lora.py trains a thin pair of grids beside a forty one by forty one
grid. This trains thin pairs beside every attention and feed forward
grid of an open model, on the chat file chapter 1 wrote, using the
libraries everybody uses for it. peft adds the adapters, trl runs the
training loop, transformers holds the model.

It needs a GPU with about eight gigabytes for the half billion
parameter model it defaults to, and it is not run in CI. On a card
rented by the hour it finishes in minutes. Install the extras first.

    pip install "agentpath-kit[training]"
    python train_lora.py clean.jsonl --output adapter

The output is the adapter alone. Measured on the default model at rank
sixteen it holds 8.8 million numbers and takes 35 megabytes, one and
three quarter percent of the base. That is what LoRA buys you, and
chapter 18 counts what it costs. merge_and_save folds it into the base
model for serving, which is the merge function of lora.py at full size.

--cpu runs it with no card at all. The same sixty five example file took
an hour and eleven minutes that way against minutes on a rented card, so
it is for watching the thing work once rather than for training anything.
"""
import argparse


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("data", help="chat JSONL from chapter 1")
    parser.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--output", default="adapter")
    parser.add_argument("--rank", type=int, default=16, help="the r of lora.py, sixteen is usual")
    parser.add_argument("--epochs", type=float, default=2.0)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--merge", action="store_true", help="also write the merged model")
    parser.add_argument(
        "--cpu",
        action="store_true",
        help="run without a GPU, slowly, which is enough to watch it work once",
    )
    arguments = parser.parse_args(argv)

    # Imported here so that the file lints and is readable without a GPU
    # and without the training extras installed.
    from datasets import load_dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import SFTConfig, SFTTrainer

    tokenizer = AutoTokenizer.from_pretrained(arguments.model)
    model = AutoModelForCausalLM.from_pretrained(arguments.model, torch_dtype="auto")
    data = load_dataset("json", data_files=arguments.data, split="train")

    # Which grids get a thin pair beside them. The attention projections
    # are the classic choice from the paper. Adding the feed forward grids
    # costs a few more parameters and usually helps, so both are listed.
    adapters = LoraConfig(
        r=arguments.rank,
        lora_alpha=2 * arguments.rank,
        lora_dropout=0.05,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"
        ],
        task_type="CAUSAL_LM",
    )

    # The trainer applies the model's own chat template to each messages
    # list, foundations chapter 7 at full size. assistant_only_loss masks
    # the user turns so the loss is on what the model should say, not on
    # what it was asked. The learning rate is about ten times what full
    # fine tuning would use, because only the adapters move and they
    # start at zero.
    settings = SFTConfig(
        output_dir=arguments.output,
        num_train_epochs=arguments.epochs,
        learning_rate=arguments.learning_rate,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        logging_steps=10,
        save_strategy="epoch",
        # bf16 is a GPU number format, so asking for it without a card stops
        # the run before it starts. --cpu turns it off and takes the hours
        # that costs, which is worth it once to see the thing work.
        bf16=not arguments.cpu,
        use_cpu=arguments.cpu,
        max_length=2048,
        assistant_only_loss=True,
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
    print(f"adapter saved to {arguments.output}")

    if arguments.merge:
        merged = trainer.model.merge_and_unload()
        merged.save_pretrained(f"{arguments.output}-merged")
        tokenizer.save_pretrained(f"{arguments.output}-merged")
        print(f"merged model saved to {arguments.output}-merged, no adapter needed to serve it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
