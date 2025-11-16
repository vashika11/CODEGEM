from transformers import GPT2LMHeadModel, GPT2Tokenizer
import torch

class PromptEngineer:
    def __init__(self):
        self.tokenizer = None
        self.model = None

    def _load_model(self):
        if self.tokenizer is None or self.model is None:
            try:
                self.tokenizer = GPT2Tokenizer.from_pretrained('gpt2')
                self.model = GPT2LMHeadModel.from_pretrained('gpt2')
                self.tokenizer.pad_token = self.tokenizer.eos_token  # Handle padding
            except Exception as e:
                raise RuntimeError(f"Failed to load GPT-2 model: {e}")

    def refine_prompt(self, user_prompt, context_history):
        try:
            self._load_model()  # Load only when needed
            # Combine prompt with recent context
            full_input = " ".join(context_history[-5:]) + " " + user_prompt  # Last 5 messages
            inputs = self.tokenizer.encode(full_input, return_tensors='pt', truncation=True, max_length=512)
            
            # Generate refined prompt
            with torch.no_grad():
                outputs = self.model.generate(inputs, max_length=100, num_return_sequences=1, no_repeat_ngram_size=2)
            refined = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return refined.strip()
        except Exception as e:
            return user_prompt  # Fallback to original prompt