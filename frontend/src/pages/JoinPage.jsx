import React, { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  FormControlLabel,
  Grid,
  MenuItem,
  Step,
  StepLabel,
  Stepper,
  TextField,
  Typography,
} from "@mui/material";
import { API } from "../services/api";

const steps = [
  "Member Information",
  "Emergency Contact",
  "Consent and Waiver",
  "Membership",
  "Review & Payment",
];

export default function JoinPage() {
  const params = new URLSearchParams(window.location.search);
  const slug = params.get("join") || "";
  const registrationSource = slug ? "sales_rep" : "front_desk";

  const [data, setData] = useState(null);
  const [activeStep, setActiveStep] = useState(0);
  const [selectedProduct, setSelectedProduct] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    participant_date_of_birth: "",
    emergency_contact_name: "",
    emergency_contact_phone: "",
    signer_relationship: "self",
    guardian_name: "",
    waiver_accepted: false,
    medical_acknowledgment: false,
    photo_release: false,
    sms_consent: false,
    email_consent: false,
    signature_name: "",
  });

  async function loadJoinData() {
    try {
      setMessage("");

      const endpoint = slug
        ? `${API}/api/join/${slug}`
        : `${API}/api/join/front-desk`;

      const res = await fetch(endpoint);
      const json = await res.json();

      if (!res.ok) {
        throw new Error(json.detail || "Could not load registration page");
      }

      setData(json);

      if (json.products?.length) {
        setSelectedProduct(json.products[0].id);
      }
    } catch (err) {
      setMessage(err.message);
    }
  }

  useEffect(() => {
    loadJoinData();
  }, []);

  function update(field, value) {
    setForm((old) => ({
      ...old,
      [field]: value,
    }));
  }

  function validateStep() {
    setMessage("");

    if (activeStep === 0) {
      if (
        !form.first_name.trim() ||
        !form.last_name.trim() ||
        !form.email.trim() ||
        !form.phone.trim() ||
        !form.participant_date_of_birth
      ) {
        setMessage("Complete all member information fields.");
        return false;
      }

      const birthDate = new Date(
        `${form.participant_date_of_birth}T00:00:00`
      );

      if (Number.isNaN(birthDate.getTime()) || birthDate > new Date()) {
        setMessage("Enter a valid date of birth.");
        return false;
      }
    }

    if (activeStep === 1) {
      const birthDate = new Date(
        `${form.participant_date_of_birth}T00:00:00`
      );
      const today = new Date();

      let participantAge =
        today.getFullYear() - birthDate.getFullYear();

      const birthdayHasOccurred =
        today.getMonth() > birthDate.getMonth() ||
        (today.getMonth() === birthDate.getMonth() &&
          today.getDate() >= birthDate.getDate());

      if (!birthdayHasOccurred) {
        participantAge -= 1;
      }

      if (
        participantAge < 18 &&
        form.signer_relationship === "self"
      ) {
        setMessage(
          "Participants under 18 must have a parent or legal guardian sign the waiver."
        );
        return false;
      }

      if (
        !form.emergency_contact_name.trim() ||
        !form.emergency_contact_phone.trim()
      ) {
        setMessage("Emergency contact information is required.");
        return false;
      }

      if (
        form.signer_relationship !== "self" &&
        !form.guardian_name.trim()
      ) {
        setMessage("Enter the parent or guardian name.");
        return false;
      }
    }

    if (activeStep === 2) {
      if (!form.waiver_accepted) {
        setMessage("The participation waiver must be accepted.");
        return false;
      }

      if (!form.medical_acknowledgment) {
        setMessage("The medical acknowledgment must be accepted.");
        return false;
      }

      if (!form.signature_name.trim()) {
        setMessage("Enter the electronic signature.");
        return false;
      }
    }


    if (activeStep === 3) {
      if (!selectedProduct) {
        setMessage("Select a membership plan to continue.");
        return false;
      }
    }

    return true;
  }

  function nextStep() {
    if (!validateStep()) {
      return;
    }

    setActiveStep((step) => Math.min(step + 1, steps.length - 1));
  }

  function previousStep() {
    setMessage("");
    setActiveStep((step) => Math.max(step - 1, 0));
  }

  async function continueToPayment() {
    if (!validateStep()) {
      return;
    }

    setSubmitting(true);
    setMessage("");

    try {
      const leadResponse = await fetch(`${API}/api/leads`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          first_name: form.first_name.trim(),
          last_name: form.last_name.trim(),
          email: form.email.trim().toLowerCase(),
          phone: form.phone.trim(),
          product_id: Number(selectedProduct),
          referral_slug: slug || null,
        }),
      });

      const lead = await leadResponse.json();

      if (!leadResponse.ok) {
        throw new Error(lead.detail || "Could not create registration");
      }

      const waiverResponse = await fetch(
        `${API}/api/waiver-submissions`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            lead_id: lead.id,
            participant_first_name: form.first_name.trim(),
            participant_last_name: form.last_name.trim(),
            participant_date_of_birth:
              form.participant_date_of_birth,
            guardian_name:
              form.signer_relationship === "self"
                ? null
                : form.guardian_name.trim(),
            signer_relationship: form.signer_relationship,
            emergency_contact_name:
              form.emergency_contact_name.trim(),
            emergency_contact_phone:
              form.emergency_contact_phone.trim(),
            waiver_accepted: form.waiver_accepted,
            medical_acknowledgment:
              form.medical_acknowledgment,
            signature_name: form.signature_name.trim(),
            signature_data: null,
            photo_release: form.photo_release,
            sms_consent: form.sms_consent,
            email_consent: form.email_consent,
          }),
        }
      );

      const waiver = await waiverResponse.json();

      if (!waiverResponse.ok) {
        throw new Error(
          waiver.detail || "Could not save waiver information"
        );
      }

      const checkoutResponse = await fetch(
        `${API}/api/clover/create-checkout/${lead.id}`,
        {
          method: "POST",
        }
      );

      const checkout = await checkoutResponse.json();

      if (!checkoutResponse.ok) {
        throw new Error(
          checkout.detail || "Could not create Clover checkout"
        );
      }

      if (!checkout.checkout_url) {
        throw new Error("Clover did not return a payment link");
      }

      window.location.href = checkout.checkout_url;
    } catch (err) {
      setMessage(err.message);
      setSubmitting(false);
    }
  }

  if (!data) {
    return (
      <Box sx={{ minHeight: "100vh", bgcolor: "#0b0b0f", p: 4 }}>
        <Typography color="white">Loading registration...</Typography>
        {message && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {message}
          </Alert>
        )}
      </Box>
    );
  }

  const selectedMembership = (data.products || []).find(
    (product) => Number(product.id) === Number(selectedProduct)
  );

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "#0b0b0f", p: 3 }}>
      <Card sx={{ maxWidth: 850, mx: "auto", borderRadius: 4 }}>
        <CardContent sx={{ p: { xs: 2, md: 4 } }}>
          <Typography variant="h3" fontWeight="bold">
            Join TNG Boxing
          </Typography>

          <Typography color="text.secondary" sx={{ mb: 3 }}>
            {registrationSource === "sales_rep"
              ? `Referred by ${data.rep_name}`
              : "Front Desk Registration"}
          </Typography>

          <Stepper
            activeStep={activeStep}
            alternativeLabel
            sx={{ mb: 4 }}
          >
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>

          {message && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {message}
            </Alert>
          )}

          {activeStep === 0 && (
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <TextField
                  required
                  fullWidth
                  label="First Name"
                  value={form.first_name}
                  onChange={(e) =>
                    update("first_name", e.target.value)
                  }
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  required
                  fullWidth
                  label="Last Name"
                  value={form.last_name}
                  onChange={(e) =>
                    update("last_name", e.target.value)
                  }
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  required
                  fullWidth
                  type="email"
                  label="Email"
                  value={form.email}
                  onChange={(e) => update("email", e.target.value)}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  required
                  fullWidth
                  label="Phone"
                  value={form.phone}
                  onChange={(e) => update("phone", e.target.value)}
                />
              </Grid>

              <Grid item xs={12}>
                <TextField
                  required
                  fullWidth
                  type="date"
                  label="Date of Birth"
                  value={form.participant_date_of_birth}
                  onChange={(e) =>
                    update(
                      "participant_date_of_birth",
                      e.target.value
                    )
                  }
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              
              <Grid item xs={12}>
                <TextField
                  required
                  select
                  fullWidth
                  label="Choose Membership"
                  value={selectedProduct}
                  onChange={(e) =>
                    setSelectedProduct(e.target.value)
                  }
                >
                  {(data.products || []).map((product) => (
               
                    <MenuItem key={product.id} value={product.id}>
                      {product.name}
                      {product.id === 3 && " (3 Months)"}
                      {product.id === 4 && " (12 Months)"}
                      {" — $"}
                      {Number(product.price || 0).toFixed(2)}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>
            </Grid>
          )}

          {activeStep === 1 && (
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <TextField
                  required
                  fullWidth
                  label="Emergency Contact Name"
                  value={form.emergency_contact_name}
                  onChange={(e) =>
                    update(
                      "emergency_contact_name",
                      e.target.value
                    )
                  }
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  required
                  fullWidth
                  label="Emergency Contact Phone"
                  value={form.emergency_contact_phone}
                  onChange={(e) =>
                    update(
                      "emergency_contact_phone",
                      e.target.value
                    )
                  }
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  select
                  fullWidth
                  label="Signer Relationship"
                  value={form.signer_relationship}
                  onChange={(e) =>
                    update(
                      "signer_relationship",
                      e.target.value
                    )
                  }
                >
                  <MenuItem value="self">Self</MenuItem>
                  <MenuItem value="parent">Parent</MenuItem>
                  <MenuItem value="guardian">Legal Guardian</MenuItem>
                </TextField>
              </Grid>

              {form.signer_relationship !== "self" && (
                <Grid item xs={12} md={6}>
                  <TextField
                    required
                    fullWidth
                    label="Parent or Guardian Name"
                    value={form.guardian_name}
                    onChange={(e) =>
                      update("guardian_name", e.target.value)
                    }
                  />
                </Grid>
              )}
            </Grid>
          )}

          {activeStep === 2 && (
            <Box>
              <Box
                sx={{
                  maxHeight: 260,
                  overflowY: "auto",
                  bgcolor: "#f5f5f5",
                  p: 2,
                  borderRadius: 2,
                  mb: 2,
                }}
              >
                <Typography variant="h6" fontWeight="bold">
                  Participation Waiver
                </Typography>

                <Typography sx={{ mt: 1, whiteSpace: "pre-line" }}>
                  I understand that boxing, fitness training,
                  sparring, strength training, conditioning, and
                  related activities involve inherent risks of
                  injury.
                  {"\n\n"}
                  I voluntarily choose to participate and accept all
                  risks associated with participation. I confirm that
                  the participant is physically able to participate
                  and will disclose relevant medical conditions to TNG
                  Boxing staff.
                  {"\n\n"}
                  I release and hold harmless TNG Boxing, TNG
                  Foundation, their owners, coaches, employees,
                  volunteers, representatives, and affiliates from
                  claims arising from ordinary risks associated with
                  participation, except where prohibited by law.
                  {"\n\n"}
                  I authorize TNG Boxing staff to contact emergency
                  services when reasonably necessary. I understand
                  that I am responsible for medical expenses incurred
                  for the participant.
                </Typography>
              </Box>

              <FormControlLabel
                control={
                  <Checkbox
                    checked={form.waiver_accepted}
                    onChange={(e) =>
                      update("waiver_accepted", e.target.checked)
                    }
                  />
                }
                label="I have read and accept the participation waiver."
              />

              <FormControlLabel
                control={
                  <Checkbox
                    checked={form.medical_acknowledgment}
                    onChange={(e) =>
                      update(
                        "medical_acknowledgment",
                        e.target.checked
                      )
                    }
                  />
                }
                label="I confirm the participant is medically able to participate and will disclose relevant health conditions."
              />

              <FormControlLabel
                control={
                  <Checkbox
                    checked={form.photo_release}
                    onChange={(e) =>
                      update("photo_release", e.target.checked)
                    }
                  />
                }
                label="I authorize TNG Boxing to use photos or videos for promotional purposes."
              />

              <FormControlLabel
                control={
                  <Checkbox
                    checked={form.sms_consent}
                    onChange={(e) =>
                      update("sms_consent", e.target.checked)
                    }
                  />
                }
                label="I agree to receive account, membership, scheduling, and promotional text messages. Consent is not required to purchase."
              />

              <FormControlLabel
                control={
                  <Checkbox
                    checked={form.email_consent}
                    onChange={(e) =>
                      update("email_consent", e.target.checked)
                    }
                  />
                }
                label="I agree to receive account, membership, scheduling, and promotional emails."
              />

              <TextField
                required
                fullWidth
                sx={{ mt: 2 }}
                label="Electronic Signature"
                helperText="Type your full legal name."
                value={form.signature_name}
                onChange={(e) =>
                  update("signature_name", e.target.value)
                }
              />
            </Box>
          )}

          {activeStep === 3 && (
            <Box>
              <Alert
                severity="success"
                sx={{
                  mb: 3,
                  borderRadius: 3,
                  fontWeight: 700,
                }}
              >
                Registration complete ? select your membership to continue.
              </Alert>

              <Typography
                variant="h4"
                fontWeight="bold"
                sx={{ mb: 1 }}
              >
                Choose Your Membership
              </Typography>

              <Typography
                color="text.secondary"
                sx={{ mb: 3 }}
              >
                Select the training option that works best for you.
                You will review everything before being sent to secure
                Clover checkout.
              </Typography>

              <Grid container spacing={2}>
                {(data.products || []).map((product) => {
                  const selected =
                    Number(selectedProduct) === Number(product.id);

                  return (
                    <Grid item xs={12} md={6} key={product.id}>
                      <Card
                        variant="outlined"
                        sx={{
                          height: "100%",
                          borderRadius: 3,
                          borderWidth: selected ? 2 : 1,
                          borderColor: selected
                            ? "error.main"
                            : "divider",
                          bgcolor: selected
                            ? "rgba(211,47,47,0.05)"
                            : "background.paper",
                          transition: "all .2s ease",
                        }}
                      >
                        <CardContent sx={{ p: 3 }}>
                          <Typography
                            variant="h6"
                            fontWeight="bold"
                          >
                            {product.name}
                          </Typography>

                          <Typography
                            variant="h3"
                            fontWeight="bold"
                            sx={{ mt: 1 }}
                          >
                            ${Number(product.price || 0).toFixed(2)}
                          </Typography>

                          <Typography
                            color="text.secondary"
                            sx={{ mt: 1, mb: 3 }}
                          >
                            TNG Boxing membership
                          </Typography>

                          <Button
                            fullWidth
                            size="large"
                            variant={
                              selected
                                ? "contained"
                                : "outlined"
                            }
                            color="error"
                            onClick={() =>
                              setSelectedProduct(product.id)
                            }
                          >
                            {selected
                              ? "Selected ?"
                              : "Select Membership"}
                          </Button>
                        </CardContent>
                      </Card>
                    </Grid>
                  );
                })}
              </Grid>

              {!selectedProduct && (
                <Typography
                  color="text.secondary"
                  textAlign="center"
                  sx={{ mt: 3 }}
                >
                  Select one membership option to continue.
                </Typography>
              )}
            </Box>
          )}

          {activeStep === 4 && (
            <Box>
              <Typography variant="h5" fontWeight="bold" sx={{ mb: 2 }}>
                Review Registration
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography color="text.secondary">
                    Participant
                  </Typography>
                  <Typography fontWeight="bold">
                    {form.first_name} {form.last_name}
                  </Typography>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Typography color="text.secondary">
                    Date of Birth
                  </Typography>
                  <Typography fontWeight="bold">
                    {form.participant_date_of_birth}
                  </Typography>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Typography color="text.secondary">Email</Typography>
                  <Typography fontWeight="bold">
                    {form.email}
                  </Typography>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Typography color="text.secondary">Phone</Typography>
                  <Typography fontWeight="bold">
                    {form.phone}
                  </Typography>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Typography color="text.secondary">
                    Emergency Contact
                  </Typography>
                  <Typography fontWeight="bold">
                    {form.emergency_contact_name}
                  </Typography>
                  <Typography>
                    {form.emergency_contact_phone}
                  </Typography>
                </Grid>

                <Grid item xs={12}>
                  <Card
                    variant="outlined"
                    sx={{
                      borderRadius: 3,
                      bgcolor: "#fafafa",
                    }}
                  >
                    <CardContent sx={{ p: 3 }}>
                      <Typography
                        variant="h6"
                        fontWeight="bold"
                        sx={{ mb: 2 }}
                      >
                        Payment Summary
                      </Typography>

                      <Box
                        sx={{
                          display: "flex",
                          justifyContent: "space-between",
                          gap: 2,
                          mb: 1.5,
                        }}
                      >
                        <Typography>
                          {selectedMembership?.name || "Membership"}
                        </Typography>

                        <Typography fontWeight="bold">
                          $
                          {Number(
                            selectedMembership?.price || 0
                          ).toFixed(2)}
                        </Typography>
                      </Box>

                      <Box
                        sx={{
                          display: "flex",
                          justifyContent: "space-between",
                          gap: 2,
                          mb: 2,
                        }}
                      >
                        <Typography>
                          New Member Registration
                        </Typography>

                        <Typography fontWeight="bold">
                          $100.00
                        </Typography>
                      </Box>

                      <Box
                        sx={{
                          borderTop: "1px solid",
                          borderColor: "divider",
                          pt: 2,
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          gap: 2,
                        }}
                      >
                        <Typography
                          variant="h6"
                          fontWeight="bold"
                        >
                          Due Today
                        </Typography>

                        <Typography
                          variant="h5"
                          fontWeight="bold"
                          color="error.main"
                        >
                          $
                          {(
                            Number(
                              selectedMembership?.price || 0
                            ) + 100
                          ).toFixed(2)}
                        </Typography>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={12}>
                  <Alert severity="info">
                    You will make one secure Clover payment for your
                    $100 registration fee plus the membership you
                    selected. Your membership access will activate
                    after payment is confirmed.
                  </Alert>
                </Grid>
              </Grid>
            </Box>
          )}

          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              mt: 4,
              gap: 2,
            }}
          >
            <Button
              variant="outlined"
              disabled={activeStep === 0 || submitting}
              onClick={previousStep}
            >
              Back
            </Button>

            {activeStep < steps.length - 1 ? (
              <Button
                variant="contained"
                color="error"
                onClick={nextStep}
              >
                Continue
              </Button>
            ) : (
              <Button
                variant="contained"
                color="error"
                size="large"
                disabled={submitting}
                onClick={continueToPayment}
              >
                {submitting
                  ? "Preparing Payment..."
                  : `Pay $${(
                      Number(selectedMembership?.price || 0) + 100
                    ).toFixed(2)} Securely with Clover`}
              </Button>
            )}
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}