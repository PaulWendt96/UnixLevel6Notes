<h1> What is a Interrupt? </h1>

An interrupt is a mechanism by which a peripheral device (i.e. something that is physically hooked up to the computer)
can ask the operating system for service. There are a variety of reasons a peripheral device might need service. For instance,
a disk driver might send an interrupt to the operating system to indicate that a byte (or a series of bytes) are ready
to be transferred from memory.

It is the operating system's job to respond to interrupts. Not all interrupts, however, are created equal. Interrupts
are given a number, 4-7, indicating the urgency of the interrupt. This priority is hard wired. 

<img src=interrupt_priority.PNG alt=PDP 11 Interrupt Priority>

Each peripheral device also has a set of two registers collectively referred to as its vector location. The first
register indicates a PC, and the second a PS. Combined, this information allows the operating system to jump 
to a handler routine (as pointed to by PC) with a specific priority and mode (as indicated by PS). Note that
the vector location for a given device is hard wired, so it is difficult to change.

From the operating system's perspective, responding to a hardware interrupt involves the following steps:

1. Save the current PC and PS registers to internal CPU registers
2. Set the PC and PS to values indicated by the vector location
3. Store the saved PC and PS to the stack (could be user or kernel; it all depends on the new PS)

Believe it or not, vector locations in the operating system are "hard wired" using a UNIX-assembler specific
directive. 


<img align="right" src=vector_locs.PNG alt=Lions vector locations> 

```c
. = 40^.
.globl start, dump
1: jmp start
   jmp dump

. = 60^.
   klin; br4
   klou; br4

. = 70^.
   pcin; br4
   pcou; br4

. = 100^.
   kwlp; br6
   kwlp; br6

/* note that "." after the 7 indicates that 7 should be interperted as decimal */
. = 114^.
   trap; br7+7.

. = 200^.
   lpou; br4

. = 220^.
   rkio; br5

. = 240^.
   trap; br7+7.
   trap; br7+8.
   trap; br7+9.
```
