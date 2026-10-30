# fsm-design

## When it applies

When the spec describes modes, phases, a protocol sequence, "states", a controller, a sequence detector, or any
behaviour of the form "after X happens, wait for Y, then do Z".

## Key rules

1. **List the states first**, with a one-line meaning each, then the transitions as a table:
   `state | condition | next state | outputs`. Check the table covers every input combination in every state.
2. **Use an enumerated type** for the state: `typedef enum logic [N-1:0] {IDLE, ...} state_t;`.
3. **Two-block style (recommended):** one `always_ff` holds `state_q`; one `always_comb` computes `state_d` and
   the outputs, with defaults at the top (`state_d = state_q;` and every output at its inactive value).
4. **Decide Moore or Mealy per output.**
   - Moore: output depends only on the state. Glitch-free, one cycle later than the input.
   - Mealy: output depends on state and inputs. Responds in the same cycle, but is combinational from the input.
   - If the spec says an output responds "in the same cycle" as an input, that output is Mealy. If it says "the
     cycle after", use Moore or a registered output.
5. **Registered (glitch-free) outputs:** decode them from `state_d` and register them (no extra lag), or
   register the decoded `state_q` (one extra cycle); pick whichever matches the spec.
6. **Reset to the idle state;** the `default` branch also goes there.
7. **"Wait N cycles" inside a state:** a separate counter that the FSM loads and watches; decide whether the
   count includes the cycle of entry.

## Usual defaults when the spec is silent (defaults, not laws)

- Binary enum encoding; synthesis may re-encode (often one-hot on FPGAs).
- Moore outputs, unless same-cycle response is required.
- A waiting state waits forever unless a timeout is specified.
- Sequence detectors: overlapping matches allowed (the common textbook default); state it as an assumption.

## Idiom

```systemverilog
module fsm_idiom (
  input  logic clk,
  input  logic rst_n,
  input  logic start,
  input  logic done_in,
  output logic busy,
  output logic done_pulse
);
  typedef enum logic [1:0] {IDLE, RUN, FINISH} state_t;
  state_t state_q, state_d;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) state_q <= IDLE;
    else        state_q <= state_d;
  end

  always_comb begin
    state_d    = state_q;
    busy       = 1'b0;
    done_pulse = 1'b0;
    unique case (state_q)
      IDLE:   if (start) state_d = RUN;
      RUN:    begin
                busy = 1'b1;
                if (done_in) state_d = FINISH;
              end
      FINISH: begin
                done_pulse = 1'b1;     // one cycle, Moore
                state_d    = IDLE;
              end
      default: state_d = IDLE;
    endcase
  end
endmodule
```

## Pitfalls

- Missing default output assignments: latches, or outputs stuck high.
- A transition one cycle late because its condition was registered first.
- A two-cycle "pulse" because the FSM stays two cycles in the state.
- An input arriving during a transition (`start` while finishing): decide and document whether it is accepted.
- Simultaneous conditions (abort and done): write the priority with `if / else if` and record it.

## How to check it

- Every state is reachable from reset and has an exit (unless terminal by design).
- Simulate each transition in the table once and check outputs on the exact cycle; lint for latches.

## Sources

- Cummings, C. E., "The Fundamentals of Efficient Synthesizable Finite State Machine Design using NC-Verilog and
  BuildGates", ICU 2002; and Cummings, C. E., "Synthesizable Finite State Machine Design Techniques Using the New
  SystemVerilog 3.0 Enhancements", SNUG San Jose 2003.
- Harris, D. M. and Harris, S. L., *Digital Design and Computer Architecture*, Morgan Kaufmann, ch. 3 (finite
  state machines).
- Mano, M. M. and Ciletti, M. D., *Digital Design*, Pearson.
