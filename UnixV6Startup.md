<h1>How does Unixv6 start?</h1>

Unix v6 starts at line 0612 in the source. At this point in time, the machine (presumably a PDP 11/40 or something similar) has nothing initialized. The goal of the Unixv6 start
sequence is to initialize a couple of things:

<h1> Segmentation Registers </h1>

The segmentation registers for user space and kernel space. These segmentation registers actually refer 
to a pair of registers: the page address register (the PAR) and the page descriptor register (the PDR). 
The page address register is used to decode virtual addresses into physical ones (with the caveat that 
this translation only occurs if the memory management unit is on). The layout of the PAR is as follows:
        
<img src=images/PAR.png alt=PAR Bitwise Layout>

The virtual addressing algorithm combines the information in the PAR with the given virtual address
to determine a physical address

<img src=images/va_to_pa_algo.PNG alt=VA Algorithm>

The PDR, on the other hand, specifies the length of the memory area (called a page - more on that later). 
The PDR also specifies permissions that control memory access. The layout of the PDR is below:

<img src=images/PDR.PNG alt=PDR Bitwise Layout>

As mentioned above, the machine actually keeps two sets of segmentation registers - one for when the
machine is in user mode, and another for one the machine is in kernel mode. The mode of the machine
is determined by a register called the Processor Status Word (PS) - but more on that later.

<img src=images/segmentation_regs.PNG alt=Segmentation Registers>

Setting the segmentation registers up appropriately will help ensure a clean split between user space
and kernel space. This setup is also relevant once we start delving into process memory.

<h1> Process #0 </h1>

Process #0 (colloquially named "The First Process") is the first process that the computer sees on 
startup. Being the first process, Process #0 requires special setup. Unix v6 starts performing this
setup on line 0646, although it takes a while for this setup to complete. 

To understand Unix, it is important to understand the ingredients of a process. In abstract terms, a 
process is a model of a computer in execution. See <a href=pdfs/lions.pdf>Lion's Chapter 7</a> or 
<a href=pdfs/unix_io_system.pdf>Thompson and Ritchies original Unix I/O paper</a> for better 
explanations than I can give. 

In concrete terms, a Unix v6 process consists of some memory (stack + heap + data segments + text), and 
some references to that memory (via a proc structure and a user structure). The proc structure contains
essential information pertaining to a process. Although the operating system only concerns itself with
one process at a time, the proc structures for each process are <b>never swapped out</b>. 

```c
/* Lines 0350 - 0376 in the source
 * The proc structure.
 * One allocated per active process.
 * Contains all data needed about the process
 * while the process may be swapped out
 * Other per process data (user.h)
 * is swapped with the process.
 */
struct proc
{
  char p_stat;
  char p_flag;
  char p_pri;    /* priority, negative is high */
  char p_sig;    /* signal number sent to this process */
  char p_uid;    /* user id, used to direct tty signals */
  char p_time;   /* resident time for scheduling */
  char p_cpu;    /* cpu usage for scheduling */
  char p_nice;   /* nice for scheduling */
  int  p_ttyp;   /* controlling tty */
  int  p_pid;    /* unique process id */
  int  p_ppid;   /* process id of parent */
  int  p_addr    /* addr of swappable image */
  int  p_size;   /* size of swappable image (*64 bytes) */
  int  p_wchan;  /* event process is awaiting */
  int  *p_textp; /* pointer to text structure */
} proc[NPROC];
```

The user structure is much larger, and contains important (but non-essential) information pertaining to
the process. As mentioned above, the operating system only concerns itself with one process at a time.
In real terms, what this means is that the operating system only works with one user structure at a time.
The "active" user structure is always found at virtual kernel address location 140000. This makes it easy
for the operating system to find and manipulate the user structure, and prevents potential complications that
could arise from more aggresive use of the MMU's addressing capabilities. 

```c
/* Lines 0400 - 0460 in the source
 * The user structure.
 * One allocated per process.
 * Contains all per process data
 * that doesn't need to be referenced
 * while the process is swapped
 * The user block is USIZE*64 bytes
 * long; resides at virtual kernel
 * loc 140000; contains the system
 * stack per user; is cross referenced
 * with theproc structure for the
 * same process
 */ 
struct user
{
  int u_rsav[2];
  int u_fsav[24];

  char u_segflg;
  char u_error;
  char u_uid;
  char u_gid;
  char u_ruid;
  char u_rgid;
  int u_procp;
  char *u_base;
  char *u_count;
  char *u_offset[2];
  int *u_cdir;
  char u_dbuf[DIRSIZ];
  char *u_dirp;
  struct {
    int u_ino;
    char u_name[DIRSIZ];
  } u_dent;
  int *u_pdir;
  int u_uisa[16];
  int u_uisd[16];
  int u_ofile[NOFILE];

  int u_arg[5];
  int u_tsize;
  int u_dsize;
  int u_ssize;
  int u_sep;
  int u_qsav[2];
  int u_ssav[2];
  int u_signal[NSIG];
  int u_utime;
  int s_utime;
  int u_cutime[2];
  int u_cstime[2];
  int *u_ar0;
  int u_prof[4];
  char u_intflg;

} u;
```
The operating system maintains a reference to the user structure through the seventh kernel segmentation address registers
(commonly referred to in the source as KISA6). <b> This is the only kernel segmentation address register that is manipulated
after startup </b>. All the other kernel segmentation registers are initialized in lines 0620 - 0630 and remain constant until
the machine shuts down. 

After initializing segmentation registers (0620 - 0645) and setting some data areas to zero (0645 - 0665), the OS source shows
a puzzling few lines of code:

```c
mov $30000, PS
jsr pc, _main
mov $170000, -(sp)
clr -(sp)
rtt
```

The first line manipulates the processor status word to indicate the previous mode as user mode and the current mode as kernel mode
(this will be important later). The second line then uses an instruction called JSR, which deserves some description. JSR has the 
following instruction format:

<i> jsr reg dest </i>

<ol>
<li> Push reg onto the stack </li>
<li> Save the current PC in reg </li>
<li> Set the PC to dest </li>
</ol>

In this case, the effect of JSR is that the current PC (which points to line 3) is pushed onto the stack, and the PC is set to 
_main (1550 in the source). But, as the commentary in Lions points out, the call on main() never returns. So why does the
code even have lines 3-5 in the first place? More on that later, but if you're curious now, check out ```bash man fork() ```.

main() starts by clearing higher areas of physical memory. The memory clearing leverages fuibyte() to determine the end of
physical memory. Each time a a memory block is found, it is initalized to zero and added to a list of free memory blocks
via a call on mfree(). 

After adding memory to the free list, main() allocates some space on the swap map so data can be swapped from main memory
to disk. 




